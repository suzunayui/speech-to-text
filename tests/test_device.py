from unittest.mock import Mock, patch

from src.transcriber import best_device, cuda_available


def test_cpu_when_nvidia_smi_is_missing() -> None:
    with patch("src.transcriber.shutil.which", return_value=None):
        assert cuda_available() is False
        assert best_device() == "cpu"


def test_cuda_when_nvidia_gpu_is_reported() -> None:
    completed = Mock(returncode=0, stdout="NVIDIA GeForce RTX\n")
    with patch("src.transcriber.shutil.which", return_value="nvidia-smi"), patch(
        "src.transcriber.subprocess.run", return_value=completed
    ):
        assert cuda_available() is True
        assert best_device() == "cuda"
