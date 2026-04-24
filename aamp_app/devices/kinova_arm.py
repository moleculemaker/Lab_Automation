# import sys
# import os
from lib2to3.pytree import Base
import time
import threading
from typing import Tuple
import yaml

# from aiohttp import TraceRequestChunkSentParams

from kortex_api.TCPTransport import TCPTransport
from kortex_api.RouterClient import RouterClient, RouterClientSendOptions
from kortex_api.SessionManager import SessionManager
from kortex_api.autogen.messages import Session_pb2

from kortex_api.autogen.client_stubs.BaseClientRpc import BaseClient
from kortex_api.autogen.client_stubs.BaseCyclicClientRpc import BaseCyclicClient
from kortex_api.autogen.messages import Base_pb2 #, BaseCyclic_pb2, Common_pb2


from .device import Device, check_initialized

TCP_PORT = 10000
# UDP_PORT = 10001


class KinovaArm(Device):
    pose_dict_file = 'robot_arm_poses.yaml'
    safe_action_names = ("Home", "Above Fork Pickup")
    
    def __init__(
            self, 
            name: str, 
            ip: str = '192.168.1.10',
            username: str = 'admin',
            password: str = 'admin',
            action_timeout: float = 20.0,
            proportional_gain: float = 2.0):
        
        super().__init__(name)
        self._ip = ip
        self._port = TCP_PORT
        self._username = username
        self._password = password
        self._action_timeout = action_timeout
        self._proportional_gain = proportional_gain
        
        with open(self.pose_dict_file) as file:
            # not safe loader
            self._post_dict = yaml.load(file, Loader=yaml.Loader)
        
        self._session_manager = None
        # move to connect?
        self._transport = TCPTransport()
        self._router = RouterClient(self._transport, RouterClient.basicErrorCallback)
        
    def get_init_args(self) -> dict:
        args_dict = {
            "name": self.name,
            "ip": self._ip,
            "username": self._username,
            "password": self._password,
            "action_timeout": self._action_timeout,
            "proportional_gain": self._proportional_gain
        }
        return args_dict
    
    def update_init_args(self, args_dict: dict):
        self.name = args_dict["name"]
        self._ip = args_dict["ip"]
        self._username = args_dict["username"]
        self._password = args_dict["password"]
        self._action_timeout = args_dict["action_timeout"]
        self._proportional_gain = args_dict["proportional_gain"]

    def connect(self) -> Tuple[bool, str]:
        self._transport.connect(self._ip, self._port)

        self._session_info = Session_pb2.CreateSessionInfo()
        self._session_info.username = self._username
        self._session_info.password = self._password
        self._session_info.session_inactivity_timeout = 10000   # (milliseconds)
        self._session_info.connection_inactivity_timeout = 2000 # (milliseconds)

        self._session_manager = SessionManager(self._router)
        self._session_manager.CreateSession(self._session_info)
        
        self._base = BaseClient(self._router)
        self._base_cyclic = BaseCyclicClient(self._router)
        
        # need to check if connection was successful?
        return (True, "Successfully connected to Kinova robot arm.")
    
    def disconnect(self) -> Tuple[bool, str]:
        if self.session_manager is not None:
            router_options = RouterClientSendOptions()
            router_options.timeout_ms = 1000 
            
            self._session_manager.CloseSession(router_options)

        self._transport.disconnect()
        
        return (True, "Successfully disconnected from Kinova robot arm.")
    
    def initialize(self) -> Tuple[bool, str]:
        was_homed, message = self.home()
        if not was_homed:
            return (False, message)
        
        was_opened, message = self.open_gripper()
        if not was_opened:
            return (False, message)

        self._is_initialized = True
        return (was_homed, "Successfully initialized Kinova arm and gripper.")
    
    def deinitialize(self) -> Tuple[bool, str]:
        pass
        
    
    def home(self) -> Tuple[bool, str]:
        for action_name in self.safe_action_names:
            was_successful, message = self.execute_action(action_name)
            if was_successful:
                return (True, message)

            if not message.startswith("Did not find action of name "):
                return (False, message)

        action_name_str = ", ".join(self.safe_action_names)
        return (False, "Can't reach safe position. None of these saved actions were found: " + action_name_str)

    def execute_action(self, action_name: str):
        # Make sure the arm is in Single Level Servoing mode
        base_servo_mode = Base_pb2.ServoingModeInformation()
        base_servo_mode.servoing_mode = Base_pb2.SINGLE_LEVEL_SERVOING
        self._base.SetServoingMode(base_servo_mode)
        
        # Move arm to ready position
        # print("Moving the arm to a safe position")
        action_type = Base_pb2.RequestedActionType()
        # action_type.action_type = Base_pb2.REACH_JOINT_ANGLES
        action_type.action_type = Base_pb2.REACH_POSE
        action_list = self._base.ReadAllActions(action_type)
        action_handle = None
        
        for action in action_list.action_list:
            if action.name == action_name:
                action_handle = action.handle

        # if not found try to find in reach joint angles
        if action_handle is None:
            action_type.action_type = Base_pb2.REACH_JOINT_ANGLES
        action_list = self._base.ReadAllActions(action_type)
        for action in action_list.action_list:
            if action.name == action_name:
                action_handle = action.handle

        if action_handle is None:
            return (False, "Did not find action of name " + action_name)

        e = threading.Event()
        notification_handle = self._base.OnNotificationActionTopic(
            self.check_for_end_or_abort(e),
            Base_pb2.NotificationOptions()
        )

        self._base.ExecuteActionFromReference(action_handle)
        finished = e.wait(self._action_timeout)
        self._base.Unsubscribe(notification_handle)

        time.sleep(0.2)

        if finished:
            return (True, action_name + " action completed")
        else:
            return (False, "Timeout on action notification wait")

    @check_initialized
    def move_arm_angular(self, pose_name: str):
        action = Base_pb2.Action()
        action.name = "Angular action movement"
        action.application_data = ""

        actuator_count = self._base.GetActuatorCount()

        pose_joint_values = self._post_dict[pose_name]
        
        # Place arm straight up
        for joint_id in range(actuator_count.count):
            joint_angle = action.reach_joint_angles.joint_angles.joint_angles.add()
            joint_angle.joint_identifier = joint_id
            joint_angle.value = pose_joint_values[joint_id]

        e = threading.Event()
        notification_handle = self._base.OnNotificationActionTopic(
            self.check_for_end_or_abort(e),
            Base_pb2.NotificationOptions()
        )
        
        # print("Executing action")
        self._base.ExecuteAction(action)

        # print("Waiting for movement to finish ...")
        finished = e.wait(self._action_timeout)
        self._base.Unsubscribe(notification_handle)

        if finished:
            return (True, "Angular movement completed")
        else:
            return (False, "Timeout on action notification wait")

    # def example_cartesian_action_movement(base, base_cyclic):
        
    #     print("Starting Cartesian action movement ...")
    #     action = Base_pb2.Action()
    #     action.name = "Example Cartesian action movement"
    #     action.application_data = ""

    #     feedback = base_cyclic.RefreshFeedback()

    #     cartesian_pose = action.reach_pose.target_pose
    #     cartesian_pose.x = feedback.base.tool_pose_x          # (meters)
    #     cartesian_pose.y = feedback.base.tool_pose_y - 0.1    # (meters)
    #     cartesian_pose.z = feedback.base.tool_pose_z - 0.2    # (meters)
    #     cartesian_pose.theta_x = feedback.base.tool_pose_theta_x # (degrees)
    #     cartesian_pose.theta_y = feedback.base.tool_pose_theta_y # (degrees)
    #     cartesian_pose.theta_z = feedback.base.tool_pose_theta_z # (degrees)

    #     e = threading.Event()
    #     notification_handle = base.OnNotificationActionTopic(
    #         check_for_end_or_abort(e),
    #         Base_pb2.NotificationOptions()
    #     )

    #     print("Executing action")
    #     base.ExecuteAction(action)

    #     print("Waiting for movement to finish ...")
    #     finished = e.wait(TIMEOUT_DURATION)
    #     base.Unsubscribe(notification_handle)

    #     if finished:
    #         print("Cartesian movement completed")
    #     else:
    #         print("Timeout on action notification wait")
    #     return finished

    # go to position at speed (requires you to know current pos because of speed sign)
    # close until stop at speed (have default)
    def open_gripper(self, grip_speed: float = 0.2):
        grip_speed = abs(grip_speed)

        gripper_command = Base_pb2.GripperCommand()
        finger = gripper_command.gripper.finger.add()
        finger.finger_identifier = 1

        gripper_command.mode = Base_pb2.GRIPPER_SPEED
        finger.value = grip_speed
        self._base.SendGripperCommand(gripper_command)
        gripper_request = Base_pb2.GripperRequest()

        # Wait for reported position to be opened
        gripper_request.mode = Base_pb2.GRIPPER_POSITION
        while True:
            gripper_measure = self._base.GetMeasuredGripperMovement(gripper_request)
            if len (gripper_measure.finger):
                # print("Current position is : {0}".format(gripper_measure.finger[0].value))
                if gripper_measure.finger[0].value < 0.05:
                    break
            else: # Else, no finger present in answer, end loop
                break
        
        wait_time = (abs(grip_speed) / 0.2 * 2 + 0.5)
        time.sleep(wait_time)
        return (True, "Successfully opened gripper")

    def close_gripper(self, grip_speed: float = -0.2):
        grip_speed = -1.0 * abs(grip_speed)

        gripper_command = Base_pb2.GripperCommand()
        finger = gripper_command.gripper.finger.add()
        finger.finger_identifier = 1

        gripper_command.mode = Base_pb2.GRIPPER_SPEED
        finger.value = grip_speed
        self._base.SendGripperCommand(gripper_command)
        gripper_request = Base_pb2.GripperRequest()

        # Wait for reported speed to be 0
        gripper_request.mode = Base_pb2.GRIPPER_SPEED
        while True:
            gripper_measure = self._base.GetMeasuredGripperMovement(gripper_request)
            if len (gripper_measure.finger):
                # print("Current speed is : {0}".format(gripper_measure.finger[0].value))
                if gripper_measure.finger[0].value == 0.0:
                    break
            else: # Else, no finger present in answer, end loop
                break
        wait_time = (abs(grip_speed) / 0.2 * 2 + 0.5)
        time.sleep(wait_time) # without this, a close then open in fast succession causes the close to end early
        return (True, "Successfully closed gripper")

    # def move_gripper(self, position: float, speed: float):
    #     # Create the GripperCommand we will send
    #     gripper_command = Base_pb2.GripperCommand()
    #     finger = gripper_command.gripper.finger.add()

    #     # Close the gripper with position increments
    #     # print("Performing gripper test in position...")
    #     gripper_command.mode = Base_pb2.GRIPPER_POSITION
    #     position = 0.00
    #     finger.finger_identifier = 1
    #     while position < 1.0:
    #         finger.value = position
    #         print("Going to position {:0.2f}...".format(finger.value))
    #         self.base.SendGripperCommand(gripper_command)
    #         position += 0.1
    #         time.sleep(1)

    #     # Set speed to open gripper
    #     print ("Opening gripper using speed command...")
    #     gripper_command.mode = Base_pb2.GRIPPER_SPEED
    #     finger.value = 0.1
    #     self.base.SendGripperCommand(gripper_command)
    #     gripper_request = Base_pb2.GripperRequest()

    #     # Wait for reported position to be opened
    #     gripper_request.mode = Base_pb2.GRIPPER_POSITION
    #     while True:
    #         gripper_measure = self.base.GetMeasuredGripperMovement(gripper_request)
    #         if len (gripper_measure.finger):
    #             print("Current position is : {0}".format(gripper_measure.finger[0].value))
    #             if gripper_measure.finger[0].value < 0.01:
    #                 break
    #         else: # Else, no finger present in answer, end loop
    #             break

    #     # Set speed to close gripper
    #     print ("Closing gripper using speed command...")
    #     gripper_command.mode = Base_pb2.GRIPPER_SPEED
    #     finger.value = -0.1
    #     self.base.SendGripperCommand(gripper_command)

    #     # Wait for reported speed to be 0
    #     gripper_request.mode = Base_pb2.GRIPPER_SPEED
    #     while True:
    #         gripper_measure = self.base.GetMeasuredGripperMovement(gripper_request)
    #         if len (gripper_measure.finger):
    #             print("Current speed is : {0}".format(gripper_measure.finger[0].value))
    #             if gripper_measure.finger[0].value == 0.0:
    #                 break
    #         else: # Else, no finger present in answer, end loop
    #             break


    @staticmethod
    def check_for_end_or_abort(e):
        """Return a closure checking for END or ABORT notifications
        Arguments:
        e -- event to signal when the action is completed
            (will be set when an END or ABORT occurs)
        """
        def check(notification, e = e):
            # print("EVENT : " + \
            #     Base_pb2.ActionEvent.Name(notification.action_event))
            if notification.action_event == Base_pb2.ACTION_END \
            or notification.action_event == Base_pb2.ACTION_ABORT:
                e.set()
        return check
