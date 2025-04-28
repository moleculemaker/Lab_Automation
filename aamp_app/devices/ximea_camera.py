from datetime import datetime
from typing import Optional, Tuple, List

from PIL import Image
# from ximea import xiapi

from .device import Device, check_initialized

# Unsure how cooperative xiapi.Camera is so did not use multiple inheritance
# will need to figure out the method resolution order if using multiple inheritance
class XimeaCamera(Device):
    save_directory = '../data/imaging/'

    def __init__(self, name: str):
        super().__init__(name)
        self.cam = xiapi.Camera()
        # defaults, changeable for each instance
        # could use dictionary but lose IDE hinting
        # could consider a namedtuple to keep descriptive context of each param while still being able to use an iterative
        # for now, individual params
        self._default_imgdataformat = 'XI_RGB24'
        self._default_exposure_time = 50000
        self._default_gain = 0.0
        # default wb coeffs below technically constants, leaving uncaptilaized
        self._default_wb_kr = 1.531
        self._default_wb_kg = 1.0
        self._default_wb_kb = 1.305
        # self.set_default_params() # done in initalize because cam is not yet open here

    def get_init_args(self) -> dict:
        args_dict = {
            "name": self.name,
        }
        return args_dict
    
    def update_init_args(self, args_dict: dict):
        self.name = args_dict["name"]

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
    def get_image(
            self, 
            save_to_file: bool = True, 
            filename: str = None, 
            exposure_time: Optional[int] = None, 
            gain: Optional[float] = None, 
            show_pop_up: bool = False) -> Tuple[bool, str]:
        # if not self._is_initialized:
        #     return (False, "Camera is not initialized")

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
            self.cam.get_image(img, timeout=(int(exposure_time / 1000 * 2)))
            self.cam.stop_acquisition()
        except xiapi.Xi_error as inst:
            return (False, "Error while getting image: " + str(inst))

        data = img.get_image_data_numpy(invert_rgb_order=True)
        img = Image.fromarray(data, 'RGB')

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

            return (True, "Successfully saved image and settings to " + str(fullfilename) + ".bmp")

        if show_pop_up:
            img.show()

        return (True, "Successfully took image but did not save.")       

    @check_initialized
    def update_white_balance(self, exposure_time: int = None, gain: Optional[float] = None) -> Tuple[bool, str]:
        # if not self._is_initialized:
        #     return (False, "Camera is not initialized")
        
        try:
            self.cam.set_manual_wb(1)
        except xiapi.Xi_error as inst:
            return (False, "Failed to set white balance: " + str(inst))

        was_successful, result_message = self.get_image(save_to_file=False, filename=None, exposure_time=exposure_time, gain=gain)

        if not was_successful:
            return (was_successful, result_message)

        return (True, "Successfully updated white balance coefficients with image: wb_kr, wb_kg, wb_kb = " + str(self.get_white_balance_rgb_coeffs()))
 
    @check_initialized # is this necessary
    def set_white_balance_manually(self, wb_kr: Optional[float] = None, wb_kg: Optional[float] = None, wb_kb: Optional[float] = None) -> Tuple[bool, str]:
        # if not self._is_initialized:
        #     return (False, "Camera is not initialized")
        
        if wb_kr is None and wb_kg is None and wb_kb is None:
            return (True, "No white balance coefficients were changed. Coefficients are currently: wb_kr, wb_kg, wb_kb = " + str(self.get_white_balance_rgb_coeffs()))
        try:
            if wb_kr is not None:
                self.cam.set_wb_kr(wb_kr)
            if wb_kg is not None:
                self.cam.set_wb_kg(wb_kg)
            if wb_kb is not None:
                self.cam.set_wb_kb(wb_kb)
        except:
            return (False, "Error in setting white balance coefficients. Coefficients are currently: wb_kr, wb_kg, wb_kb = " + str(self.get_white_balance_rgb_coeffs()))
        
        return (True, "Successfully set white balance coefficients manually: wb_kr, wb_kg, wb_kb = " + str(self.get_white_balance_rgb_coeffs()))
    
    @check_initialized # is this necessary
    def reset_white_balance_rgb_coeffs(self) -> Tuple[bool, str]:
        self.cam.set_wb_kr(self._default_wb_kr)
        self.cam.set_wb_kg(self._default_wb_kg)
        self.cam.set_wb_kb(self._default_wb_kb)
        return (True, "Successfully reset white balance coefficients to defaults. Coefficients are currently: wb_kr, wb_kg, wb_kb = " + str(self.get_white_balance_rgb_coeffs()))

    @check_initialized # is this necessary
    def get_white_balance_rgb_coeffs(self) -> List[float]:
        wb = []
        wb.append(self.cam.get_wb_kr())
        wb.append(self.cam.get_wb_kg())
        wb.append(self.cam.get_wb_kb())
        return wb



