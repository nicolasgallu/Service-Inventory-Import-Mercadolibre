from app.service.notifications import enviar_mensaje_whapi
import pytest



def test_empty_response():
    with pytest.raises(TypeError) as excinfo:
        assert enviar_mensaje_whapi("token", "123456", "mensaje")