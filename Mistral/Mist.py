import os
from mistralai import Mistral

#start of new implementation

api_key = os.environ.get('MISTRAL_API_KEY')
                         
model = "pixtral-12b-2409"

client = Mistral(api_key=api_key)



class AIModelClass:
    college_name = ""
    bot_name = ""
    message_history = []
    
    role_types = ['system', 'assistant', 'user']
    
    #TODO: make save message history function and load message history function

    # Runs on instance of class creation
    def __init__(self, college_name, bot_name):
        self.college_name = college_name
        self.bot_name = bot_name
        #system prompts, these are what control the AI's rule set and what it should follow over what the user says
        self.add_system_prompt(f"""You are a helpful assistant tasked with promoting {college_name}. 
        Ensure all responses focus solely on {college_name}, its programs, values, achievements, and unique offerings. 
        Avoid mentioning other institutions or making comparisons unless specifically asked to do so by the user.

        try to keep things concise as possible, while still keeping the conversational/professional tone.

        Ensure that responses to prospective student questions use varied sentence structures and tones to keep the conversation engaging. 
        Avoid reusing exact phrasing from the initial email.
        Prompt a few questions the user can ask you the assistant about the school. Questions like 'What degrees does neumont offer?'

        Do not suggest questions that have either already been answered or have been asked before.""")
        
        self.training_data()
        
    def create_message(self, role: str, message: str):
        return {"role": role, "content":message}

    def add_system_prompt(self, msg):
        message = self.create_message("system", msg)
        self.message_history.append(message)

    def add_user_prompt(self, msg):
        message = self.create_message("user", msg)
        self.message_history.append(message)
        
    def add_assistant_prompt(self, msg):
        message = self.create_message("system", msg)
        self.message_history.append(message)

    def get_chat_response(self, msg):
        self.add_user_prompt(msg)
        
        chat_response = client.chat.complete(
            model=model,
            messages=self.message_history
        )
        
        agent_message = chat_response.choices[0].message.content
        self.add_assistant_prompt(agent_message)
        
        return agent_message
    
    def training_data(self):
        self.add_user_prompt("What scholarships do you offer?")
        self.add_assistant_prompt(f"""Great question!
                        {college_name} offers a variety of scholarships, including merit-based awards for academic excellence, need-based assistance, and special grants for extracurricular achievements. 
                        Our admissions team is happy to guide you through the application process.
                        Let me know if you'd like more details on specific opportunities!""")
    
    
if __name__ == "__main__":
    college_name = "Neumont College of Computer Science"
    bot_name = "Billy"
    
    AIModel = AIModelClass(college_name, bot_name)

    AIModel.add_user_prompt(f"""Write a casual and inviting email to promote {college_name} to prospective students and their families. 
                    Use a friendly and personal tone. Highlight the school's unique features, such as academic programs, campus life, and opportunities for growth, in a concise manner. 
                    Mention that you are an AI assistant and encourage the recipient to reply with any questions they might have, offering examples of questions they can ask. 
                    Keep the email short and engaging.""")

    #prints original email
    chat_response = client.chat.complete(
            model=model,
            messages=AIModel.message_history
        )
    print(chat_response.choices[0].message.content)

    #proper user loop
    while True:
        user_message = input(">: ")
        response = AIModel.get_chat_response(user_message)
        print(response)