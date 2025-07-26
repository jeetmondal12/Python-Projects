import google.generativeai as genai

API_KEY = "AIzaSyCsKuFEfKVC4C-XzKbRctuckrtYhFbYw7g"
genai.configure(api_key=API_KEY)

model = genai.GenerativeModel("gemini-2.0-flash")
chat=model.start_chat()

print("Welcome to Gemini 2.0 Flash! You can start chatting now.")
while True:
    user_input = input("You: ")
    if user_input.lower() in ["exit", "quit", "bye"]:
        print("Exiting the chat. Goodbye!")
        break

    response = chat.send_message(user_input)
    print(f"Gemini: {response.text}")