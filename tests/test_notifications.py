from app.service.notifications import enviar_mensaje_whapi
import pytest

def test_bad_phone_type():
    with pytest.raises(TypeError) as excinfo:
        enviar_mensaje_whapi("token", "123456", "mensaje")

def test_empty_message():
    with pytest.raises(ValueError) as excinfo:
        enviar_mensaje_whapi("token", "123456", None)