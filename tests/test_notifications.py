from app.service.notifications import enviar_mensaje_whapi

message= f'Nueva Orden Generada desde {"mercadolibre"}\n {2000016439211050}'
enviar_mensaje_whapi("6rpLCFQjVDJTJKSlhfaDlaPqawjAfDHJ", 5493517691131, message)
print("mensaje enviado")