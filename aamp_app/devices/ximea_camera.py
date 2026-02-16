from datetime import datetime
from typing import Optional, Tuple, List

from PIL import Image
from ximea import xiapi

from .device import Device, check_initialized

import numpy as np
import cv2


# Unsure how cooperative xiapi.Camera is so did not use multiple inheritance
# will need to figure out the method resolution order if using multiple inheritance
class XimeaCamera(Device):
    save_directory = 'data/imaging/'

    def __init__(self, name: str):
        super().__init__(name)
        self.cam = xiapi.Camera()
        # defaults, changeable for each instance
        # could use dictionary but lose IDE hinting
        # could consider a namedtuple to keep descriptive context of each param while still being able to use an iterative
        # for now, individual params
        self._default_imgdataformat = 'XI_RGB24'
        # self._default_imgdataformat = 'XI_MONO8'
        self._default_exposure_time = 50000
        self._default_gain = 0.0
        # default wb coeffs below technically constants, leaving uncaptilaized

        self._default_wb_kr = 1.531
        self._default_wb_kg = 1.0
        self._default_wb_kb = 1.305

        self.background = None
        self.completeness_ref = None

        self.boundaryx_0 = 350
        self.boundaryx_1 = 1000
        # self.set_default_params() # done in initalize because cam is not yet open here

    # no setter for imgdataformat at the moment
    @property
    def default_imgdataformat(self) -> str:
        return self._default_imgdataformat

    @property
    def default_exposure_time(self) -> int:
        return self._default_exposure_time

    @default_exposure_time.setter
    def default_exposure_time(self, exposure_time: int):
        if exposure_time > 0:
            self._default_exposure_time = int(exposure_time)

    @property
    def default_gain(self) -> float:
        return self._default_gain

    @default_gain.setter
    def default_gain(self, gain: float):
        # there is an upper limit for this but not 100% sure what it is
        if gain >= 0.0:
            self._default_gain = gain

    # no setter for default wb coeffs
    @property
    def default_wb_kr(self) -> float:
        return self._default_wb_kr

    @property
    def default_wb_kg(self) -> float:
        return self._default_wb_kg

    @property
    def default_wb_kb(self) -> float:
        return self._default_wb_kb

    def set_default_params(self):
        self.cam.set_imgdataformat(self._default_imgdataformat)
        self.cam.set_exposure(self._default_exposure_time)
        self.cam.set_gain(self._default_gain)
        self.cam.set_wb_kr(self._default_wb_kr)
        self.cam.set_wb_kg(self._default_wb_kg)
        self.cam.set_wb_kb(self._default_wb_kb)

    def initialize(self, set_defaults: bool = True) -> Tuple[bool, str]:
        try:
            self.cam.open_device()
            # set defaults if flag is True. This should be True the very first time in order to set the default params, but not enforced
            if set_defaults:
                self.set_default_params()
                print(self.cam.get_exposure_minimum())
                print(self.cam.get_exposure_maximum())
                print(self.cam.get_exposure_increment())
                print("Gain min:", self.cam.get_gain_minimum())
                print("Gain max:", self.cam.get_gain_maximum())
                print("Gain increment:", self.cam.get_gain_increment())
                print("Auto white balance?", self.cam.is_auto_wb())
                self.cam.disable_aeag()
                # self.cam.enable_auto_wb()
                # print()
            self._is_initialized = True
        except xiapi.Xi_error as inst:
            self._is_initialized = False
            return (False, "Failed to connect and initialize: " + str(inst))

        if set_defaults:
            return (True, "Successfully initialized camera by opening communications and setting defaults.")
        else:
            return (True, "Successfully intitialized camera by opening communications.")

    def deinitialize(self, reset_init_flag: bool = True) -> Tuple[bool, str]:
        try:
            self.cam.stop_acquisition()
            self.cam.close_device()
        except xiapi.Xi_error as inst:
            return (False, "Failed to deinitialize the camera: " + str(inst))

        if reset_init_flag:
            self._is_initialized = False

        return (True, "Successfully deinitialized camera, communication closed.")

    @check_initialized
    def update_background(
            self,
            save_to_file: bool = True,
            filename: str = None,
            exposure_time: Optional[int] = None,
            gain: Optional[float] = None) -> Tuple[bool, str]:
        if exposure_time is None:
            exposure_time = self._default_exposure_time
        if gain is None:
            gain = self._default_gain

        try:
            self.cam.set_exposure(exposure_time)
            self.cam.set_gain(gain)

            img = xiapi.Image()
            self.cam.start_acquisition()
            self.cam.get_image(img)
            self.cam.stop_acquisition()
        except xiapi.Xi_error as inst:
            return (False, "Error while getting image: " + str(inst))

        data = img.get_image_data_numpy(invert_rgb_order=True)
        self.background = data
        img = Image.fromarray(self.background, 'RGB')

        if save_to_file:

            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = timestamp
            fullfilename = self.save_directory + filename
            img.save(fullfilename + '.bmp')

        return (True, "Successfully update background")

    # @check_initialized
    # def is_uniform(
    #         self,
    #         save_to_file: bool = True,
    #         exposure_time: Optional[int] = None,
    #         gain: Optional[float] = None) -> float:
    #     if exposure_time is None:
    #         exposure_time = self._default_exposure_time
    #     if gain is None:
    #         gain = self._default_gain

    #     try:
    #         self.cam.set_exposure(exposure_time)
    #         self.cam.set_gain(gain)
    #         img = xiapi.Image()
    #         self.cam.start_acquisition()
    #         self.cam.get_image(img)
    #         self.cam.stop_acquisition()
    #     except xiapi.Xi_error as inst:
    #         return (False, "Error while getting image: " + str(inst))
    #     data = img.get_image_data_numpy(invert_rgb_order=True)

    #     # define a square area, check uniform
    #     x_upper = 680
    #     y_upper = 540
    #     length = 500
    #     checking_area = data[y_upper : y_upper+length, x_upper: x_upper + length, :]
    #     std = 0
    #     for i in range (3):
    #         avg = np.average(checking_area[:,:,i])
    #         sqaure_diff = (checking_area[:,:,i] - avg) ** 2
    #         std += np.sqrt(np.average(sqaure_diff))
    #     score = 1 - std / (127.5 * 3)

    #     checking_area = data[y_upper : y_upper+length, x_upper: x_upper + length, :]
    #     img_focus = Image.fromarray(checking_area, 'RGB')

    #     if save_to_file:

    #         if filename is None:
    #             timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    #             filename = timestamp
    #         fullfilename = self.save_directory + filename
    #         img_focus.save(fullfilename + '_focus' + '.bmp')

    #     return score

    @check_initialized
    def get_image(
            self,
            save_to_file: bool = True,
            filename: str = None,
            check_uniform: bool = True,
            y_upper: int = 20,
            y_length: int = 1000,
            x_upper: int = None,
            x_length: int = None,
            exposure_time: Optional[int] = None,
            gain: Optional[float] = None,
            show_pop_up: bool = False) -> Tuple[bool, str]:
        # if not self._is_initialized:
        #     return (False, "Camera is not initialized")



        if x_upper is None:
            x_upper = self.boundaryx_0
        if x_length is None:
            x_length = self.boundaryx_1 - self.boundaryx_0
        print('x_upper:', x_upper)
        print('x_length:', x_length)
        if exposure_time is None:
            exposure_time = self._default_exposure_time
        if gain is None:
            gain = self._default_gain

        try:
            self.cam.set_exposure(exposure_time)
            self.cam.set_gain(gain)
            img = xiapi.Image()
            self.cam.start_acquisition()
            # exposure time is in microsec, timeout is in millisec, timeout is set to double the exposure time
            # self.cam.get_image(img, timeout=(int(exposure_time / 1000 * 2)))
            self.cam.get_image(img)
            # data_raw = img.get_image_data_raw()
            # data_0 = list(data_raw)
            # print("first 10 pixels: " + str(data_0[:10]))
            self.cam.stop_acquisition()
        except xiapi.Xi_error as inst:
            return (False, "Error while getting image: " + str(inst))

        # print("Current image format:", self.cam.get_imgdataformat())

        data = img.get_image_data_numpy(invert_rgb_order=True)
        img = Image.fromarray(data, 'RGB')

        # print("data:",data.dtype)
        print("shape: ", data.shape)
        # print("first 10 value:", data[0:10,0,:])

        if check_uniform:
            if self.background is None:
                checking_area = data[y_upper: y_upper + y_length, x_upper: x_upper + x_length, :]
            else:
                corrected_image = cv2.subtract(self.background, data)
                print("shape of corrected_image", corrected_image.shape)
                checking_area = corrected_image[y_upper: y_upper + y_length, x_upper: x_upper + x_length]
                checking_area[checking_area < 0] = 0
            std = 0
            for i in range(3):
                std += (np.std(checking_area[:, :, i])) ** 2
            score = 1 - np.sqrt(std) / (220.836)
            img_focus = Image.fromarray(checking_area, 'RGB')
            print("uniformity score is ", score)

        if save_to_file:

            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = timestamp
            fullfilename = self.save_directory + filename
            img.save(fullfilename + '.bmp')

            settings = ["image data format = " + self.cam.get_imgdataformat() + "\n",
                        "exposure (us) = " + str(self.cam.get_exposure()) + "\n",
                        "gain = " + str(self.cam.get_gain()) + "\n",
                        "wb_kr = " + str(self.cam.get_wb_kr()) + "\n",
                        "wb_kg = " + str(self.cam.get_wb_kg()) + "\n",
                        "wb_kb = " + str(self.cam.get_wb_kb()) + "\n"]
            with open(fullfilename + '.txt', 'w') as file:
                file.writelines(settings)

            if check_uniform:
                img_focus.save(fullfilename + '_checkunifrom' + '.bmp')
                settings = ["This sample is " + str(score * 100) + "% uniform, (1 - std / 127.5) " + "\n",
                            "checking area:"  "\n",
                            "x from " + str(x_upper) + " to " + str(x_upper + x_length) + "\n",
                            "y from " + str(y_upper) + " to " + str(y_upper + y_length) + "\n"]
                with open(fullfilename + '_checkunifrom' + '.txt', 'w') as file:
                    file.writelines(settings)

            return (True, "Successfully saved image and settings to " + str(fullfilename) + ".bmp")

        if show_pop_up:
            img.show()

        return (True, "Successfully took image but did not save.")

    @check_initialized
    def update_vertical_bound(
            self,
            exposure_time: Optional[int] = None,
            gain: Optional[float] = None) -> Tuple[bool, str]:
        if self.background is None:
            return (False, "background image is required, call update_background first")
        if exposure_time is None:
            exposure_time = self._default_exposure_time
        if gain is None:
            gain = self._default_gain

        try:
            self.cam.set_exposure(exposure_time)
            self.cam.set_gain(gain)

            img = xiapi.Image()
            self.cam.start_acquisition()
            # exposure time is in microsec, timeout is in millisec, timeout is set to double the exposure time
            self.cam.get_image(img)
            self.cam.stop_acquisition()
        except xiapi.Xi_error as inst:
            return (False, "Error while getting image: " + str(inst))

        data = img.get_image_data_numpy(invert_rgb_order=True)
        gray_scale_ref = cv2.subtract(cv2.cvtColor(self.background, cv2.COLOR_RGB2GRAY),
                                      cv2.cvtColor(data, cv2.COLOR_RGB2GRAY))
        gray_scale_ref[gray_scale_ref < 5] = 0
        gray_scale_ref[gray_scale_ref >= 5] = 100
        boundary = np.abs(gray_scale_ref[:, 1:] - gray_scale_ref[:, :-1])
        img = Image.fromarray(boundary, 'L')
        img.save(self.save_directory + 'z_bbs' + '.bmp')
        print('boundary.shape', boundary.shape)
        boundary = boundary.astype(np.int32)
        boundary = np.sum(boundary, axis=0)

        # remainder = len(boundary) % 10
        # if remainder != 0:
        #     padding = 10 - remainder
        #     boundary_pad = np.pad(boundary, (0,padding), "constant")
        # else:
        #     boundary_pad = boundary
        # boundary_reshape = (boundary_pad.reshape(-1,10)).sum(axis=1)

        boundary_x = np.argsort(boundary)
        print('boundary_x:', boundary_x[-10:])
        print(boundary.argmin(), boundary.argmax(), boundary.min(), boundary.max())
        print(boundary[boundary_x[-10:]])

        self.boundaryx_0 = boundary_x[-1]
        boundaryx_1_idx = -1
        while (np.abs(boundary_x[boundaryx_1_idx] - self.boundaryx_0) < 600):
            boundaryx_1_idx -= 1
        self.boundaryx_1 = boundary_x[boundaryx_1_idx]

        if self.boundaryx_1 < self.boundaryx_0:
            temp = self.boundaryx_1
            self.boundaryx_1 = self.boundaryx_0
            self.boundaryx_0 = temp
        print('self.boundaryx_0:', self.boundaryx_0)
        print('self.boundaryx_1:', self.boundaryx_1)
        self.boundaryx_0 += 60
        self.boundaryx_1 -= 60

        return (True, "Successfully update vertical boundary")

    @check_initialized
    def update_completeness_ref(
            self,
            save_to_file: bool = True,
            filename: str = None,
            exposure_time: Optional[int] = None,
            gain: Optional[float] = None) -> Tuple[bool, str]:
        if self.background is None:
            return (False, "background image is required, call update_background first")
        if exposure_time is None:
            exposure_time = self._default_exposure_time
        if gain is None:
            gain = self._default_gain

        try:
            self.cam.set_exposure(exposure_time)
            self.cam.set_gain(gain)

            img = xiapi.Image()
            self.cam.start_acquisition()
            # exposure time is in microsec, timeout is in millisec, timeout is set to double the exposure time
            self.cam.get_image(img)
            self.cam.stop_acquisition()
        except xiapi.Xi_error as inst:
            return (False, "Error while getting image: " + str(inst))

        data = img.get_image_data_numpy(invert_rgb_order=True)
        gray_scale_ref = cv2.subtract(cv2.cvtColor(self.background, cv2.COLOR_RGB2GRAY),
                                      cv2.cvtColor(data, cv2.COLOR_RGB2GRAY))
        gray_scale_ref[gray_scale_ref < 5] = 0
        gray_scale_ref[gray_scale_ref >= 5] = 100
        self.completeness_ref = gray_scale_ref
        img = Image.fromarray(self.completeness_ref, 'L')

        if save_to_file:

            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = timestamp
            fullfilename = self.save_directory + filename
            img.save(fullfilename + '.bmp')

        return (True, "Successfully update completeness reference")

    @check_initialized
    def check_completeness(
            self,
            save_to_file: bool = True,
            filename: str = None,
            exposure_time: Optional[int] = None,
            gain: Optional[float] = None) -> Tuple[bool, str]:
        if self.completeness_ref is None:
            return (False, "completeness_ref image is required, call update_completeness_ref first")
        if exposure_time is None:
            exposure_time = self._default_exposure_time
        if gain is None:
            gain = self._default_gain

        try:
            self.cam.set_exposure(exposure_time)
            self.cam.set_gain(gain)

            img = xiapi.Image()
            self.cam.start_acquisition()
            # exposure time is in microsec, timeout is in millisec, timeout is set to double the exposure time
            self.cam.get_image(img)
            self.cam.stop_acquisition()
        except xiapi.Xi_error as inst:
            return (False, "Error while getting image: " + str(inst))

        data = img.get_image_data_numpy(invert_rgb_order=True)
        gray_scale_image = cv2.subtract(cv2.cvtColor(self.background, cv2.COLOR_RGB2GRAY),
                                        cv2.cvtColor(data, cv2.COLOR_RGB2GRAY))
        gray_scale_image[gray_scale_image < 5] = 0
        gray_scale_image[gray_scale_image >= 5] = 100
        similarity = 1 - np.sum(np.abs(gray_scale_image - self.completeness_ref)) / (
                    np.sum(np.ones_like(gray_scale_image)) * 100)
        img = Image.fromarray(gray_scale_image, 'L')

        if save_to_file:

            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = timestamp
            fullfilename = self.save_directory + filename
            img.save(fullfilename + '.bmp')

        return (True, "This sample's shape is " + str(similarity * 100) + "% similar to the reference.")

    @check_initialized
    def update_white_balance(self, exposure_time: int = None, gain: Optional[float] = None) -> Tuple[bool, str]:
        # if not self._is_initialized:
        #     return (False, "Camera is not initialized")

        try:
            self.cam.set_manual_wb(1)
        except xiapi.Xi_error as inst:
            return (False, "Failed to set white balance: " + str(inst))

        was_successful, result_message = self.get_image(save_to_file=False, filename=None, exposure_time=exposure_time,
                                                        gain=gain)

        if not was_successful:
            return (was_successful, result_message)

        return (True, "Successfully updated white balance coefficients with image: wb_kr, wb_kg, wb_kb = " + str(
            self.get_white_balance_rgb_coeffs()))

    @check_initialized  # is this necessary
    def set_white_balance_manually(self, wb_kr: Optional[float] = None, wb_kg: Optional[float] = None,
                                   wb_kb: Optional[float] = None) -> Tuple[bool, str]:
        # if not self._is_initialized:
        #     return (False, "Camera is not initialized")

        if wb_kr is None and wb_kg is None and wb_kb is None:
            return (True,
                    "No white balance coefficients were changed. Coefficients are currently: wb_kr, wb_kg, wb_kb = " + str(
                        self.get_white_balance_rgb_coeffs()))
        try:
            if wb_kr is not None:
                self.cam.set_wb_kr(wb_kr)
            if wb_kg is not None:
                self.cam.set_wb_kg(wb_kg)
            if wb_kb is not None:
                self.cam.set_wb_kb(wb_kb)
        except:
            return (False,
                    "Error in setting white balance coefficients. Coefficients are currently: wb_kr, wb_kg, wb_kb = " + str(
                        self.get_white_balance_rgb_coeffs()))

        return (True, "Successfully set white balance coefficients manually: wb_kr, wb_kg, wb_kb = " + str(
            self.get_white_balance_rgb_coeffs()))

    @check_initialized  # is this necessary
    def reset_white_balance_rgb_coeffs(self) -> Tuple[bool, str]:
        self.cam.set_wb_kr(self._default_wb_kr)
        self.cam.set_wb_kg(self._default_wb_kg)
        self.cam.set_wb_kb(self._default_wb_kb)
        return (True,
                "Successfully reset white balance coefficients to defaults. Coefficients are currently: wb_kr, wb_kg, wb_kb = " + str(
                    self.get_white_balance_rgb_coeffs()))

    @check_initialized  # is this necessary
    def get_white_balance_rgb_coeffs(self) -> List[float]:
        wb = []
        wb.append(self.cam.get_wb_kr())
        wb.append(self.cam.get_wb_kg())
        wb.append(self.cam.get_wb_kb())
        return wb
