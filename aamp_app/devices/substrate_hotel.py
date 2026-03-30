from .substrate_linear_stage_base import SubstrateLinearStageBase


class SubstrateHotel(SubstrateLinearStageBase):
    """Arduino-controlled linear stage for the substrate hotel."""

    def __init__(
            self,
            name: str,
            port: str,
            max_position_mm: float = 430.0,
            baudrate: int = 9600,
            timeout: float = 1.0,
            connect_delay_s: float = 5.0,
            ready_timeout_s: float = 5.0,
            home_timeout_s: float = 300.0,
            move_timeout_s: float = 300.0):
        super().__init__(
            name=name,
            port=port,
            max_position_mm=max_position_mm,
            baudrate=baudrate,
            timeout=timeout,
            connect_delay_s=connect_delay_s,
            ready_timeout_s=ready_timeout_s,
            home_timeout_s=home_timeout_s,
            move_timeout_s=move_timeout_s,
        )
