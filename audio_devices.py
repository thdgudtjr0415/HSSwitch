"""
Windows에 연결된 재생(스피커/헤드셋) 장치와 녹음(마이크) 장치 목록을
조회하는 모듈. pycaw의 공식 문서 예제 패턴을 그대로 따른다.

이 모듈의 함수들은 tkinter 메인 스레드뿐 아니라 pywebview의 JS-Python 브리지
콜백 스레드(트레이 팝업)에서도 호출될 수 있어서 어느 스레드에서 불릴지 알 수
없다. volume_control.py와 동일하게, 매 호출마다 자체적으로 COM을 초기화한다
(이미 초기화된 스레드에서 다시 불러도 안전하고, 호출 스레드 종류에 의존하지 않게
된다).
"""

import warnings
from dataclasses import dataclass

import comtypes
from pycaw.constants import DEVICE_STATE, EDataFlow
from pycaw.pycaw import AudioUtilities


@dataclass
class DeviceInfo:
    id: str
    name: str


def _get_devices(data_flow: int) -> list[DeviceInfo]:
    # 부팅 직후(특히 --startup으로 자동 실행될 때)는 Windows 오디오 서비스나
    # 무선 장치 동글이 아직 준비되지 않아 GetAllDevices 자체가 COM 예외를 던질 수 있다.
    # 여기서 예외가 새 나가면 호출한 쪽(트레이 앱 초기화 스레드)이 통째로 죽어버려서
    # 프로그램이 아무 반응 없이 실행 안 되는 것처럼 보이므로, 실패하면 빈 목록을 돌려준다.
    comtypes.CoInitialize()
    try:
        with warnings.catch_warnings():
            # 일부 비활성/특수 장치에서 COMError 경고가 뜨는데 무시해도 무방
            warnings.simplefilter("ignore", UserWarning)
            devices = AudioUtilities.GetAllDevices(
                data_flow=data_flow, device_state=DEVICE_STATE.ACTIVE.value
            )
    except Exception:
        return []

    result = []
    for d in devices:
        try:
            result.append(DeviceInfo(id=d.id, name=d.FriendlyName))
        except Exception:
            continue
    return result


def get_playback_devices() -> list[DeviceInfo]:
    """스피커, 헤드셋 등 출력(재생) 장치 목록"""
    return _get_devices(EDataFlow.eRender.value)


def get_recording_devices() -> list[DeviceInfo]:
    """마이크 등 입력(녹음) 장치 목록"""
    return _get_devices(EDataFlow.eCapture.value)


def get_default_playback_id() -> str | None:
    comtypes.CoInitialize()
    try:
        return AudioUtilities.GetSpeakers().id
    except Exception:
        return None


def get_default_recording_id() -> str | None:
    comtypes.CoInitialize()
    try:
        device_enumerator = AudioUtilities.GetDeviceEnumerator()
        # eCapture=1, eMultimedia=1
        endpoint = device_enumerator.GetDefaultAudioEndpoint(1, 1)
        return AudioUtilities.CreateDevice(endpoint).id
    except Exception:
        return None
