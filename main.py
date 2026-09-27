from orquestador import clasificar_intencion
from agent import conversar as conversar_agenda
from faq_agent import responder_faq

if __name__ == "__main__":
    print("Barbería Andres - Asistente (escribe 'salir' para terminar)\n")
    historial = []

    while True:
        entrada = input("Cliente: ")
        if entrada.lower() == "salir":
            break

        historial.append({"role": "user", "content": entrada})
        categoria = clasificar_intencion(historial)  # ← debe decir "historial", no "entrada"

        if categoria == "agenda":
            respuesta_texto, historial = conversar_agenda(historial, entrada, canal="agenda")
        elif categoria == "faq":
            respuesta_texto, historial = responder_faq(historial, entrada)
        else:
            respuesta_texto = "Disculpa, no entendí bien tu solicitud. ¿Podrías reformularla?"
            historial.append({"role": "assistant", "content": respuesta_texto})

        print(f"Asistente: {respuesta_texto}\n")