import os
import json
from dotenv import load_dotenv
from crewai import Agent, Task, Crew
from langchain_groq import ChatGroq
from groq import Groq
from langchain_core.prompts import ChatPromptTemplate
from helpers import parse_json_garbage, get_actions_taken, get_actions_taken_with_thoughts
from agent.prompt import FIRST_STEP_ACTION_DESCRIPTION_PROMPT, FIRST_STEP_ACTION_GOAL_PROMPT, NEXT_STEP_ACTION_DESCRIPTION_PROMPT, NEXT_STEP_ACTION_GOAL_PROMPT

load_dotenv()


class PragyaGPT:
    def __init__(self, model=None):
        self.available_model = ['llama3-8b-8192', 'llama3-70b-8192', 'llama2-70b-4096'
                                'mixtral-8x7b-32768', 'gemma-7b-it']
        self.model = model if model else self.available_model[1]
        self.max_tokens = 2048

        self.history = []
        self.actions_taken = []
        self.temp_objective: str = None
        self.final_goal: str = None

        self.client = Groq(
            api_key=os.environ.get("GROQ_API_KEY"),
        )

    def get_final_goal(self, objective):

        system_prompt = """ROLE: "Final_Goal_Decider_Agent"

        GOAL: "Clarify the final goal that user wants to solve, finish the objective with there requirements and at the end after the goal is achieved give an answer to the user's objective(question)."

        BACKSTORY: "You are an expert in deciding the final goal of user's objective.
        Your goal is to give an final goal with the help of user's objective ensuring the objective is achieved with the help of browser."
        """

        user_prompt = """DESCRIPTION: "What will be the final goal for the user's objective?"

        USER'S OBJECTIVE: "{objective}"

        EXPECTED OUTPUT: "A short, simple and precise goal that user wants to achieve with the help of browser. Only give the final goal in the response nothing else. And also what could be the possible steps to achieve the final goal."
        """.format(objective=objective)

        chat_completion = self.client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            model=self.model,
            temperature=1,
            stream=False,
            top_p=1,
            stop=None,
            # response_format={"type": "json_object"}, # Enable JSON mode by setting the response format
        )

        response = chat_completion.choices[0].message.content
        self.final_goal = response

        return response

    def get_first_step(self, objective, error=None):
        system = """ROLE: "Human like robot browsing the web."

        GOAL: "Give next action with your thoughts needed to perform in browser."

        BACKSTORY: "You are expert in deciding what to do next. 
        You always browse the web and visit different websites to perform some actions with logical thoughts.
        Your goal is to give an next capable, concise, simple and logical action and yout thoughts on it from user's objective, final goal, current page elements and past action with it thoughts,
        ensuring the objective is achieved with the help of browser."
        """
        human = """{description_prompt}
        {FIRST_STEP_ACTION_GOAL_PROMPT}
        """.format(
            description_prompt=FIRST_STEP_ACTION_DESCRIPTION_PROMPT.format(
                objective=objective, final_goal=self.final_goal, error=error
            ),
            FIRST_STEP_ACTION_GOAL_PROMPT=FIRST_STEP_ACTION_GOAL_PROMPT
        )

        chat = []
        chat.append({
            "role": "system",
            "content": system
        })
        chat.append({
            "role": "user",
            "content": human
        })

        self.history.extend(chat)  # Add chat to history

        chat_completion = self.client.chat.completions.create(
            messages=chat,
            model=self.model,
            temperature=1,
            stream=False,
            top_p=1,
            stop=None,
            # Enable JSON mode by setting the response format
            response_format={"type": "json_object"},
        )

        response = chat_completion.choices[0].message.content
        json_response = parse_json_garbage(response)
        print("\nFIRST STEP RESPONSE:\n")
        print(json.dumps(json_response, indent=4))
        print("\n")

        self.history.append(
            {
                "role": "assistant",
                "content": json_response
            }
        )  # Add assistant response to history
        self.actions_taken.append(json_response)

        return json_response

    def _observation(self, current_url, current_page_elements):

        system = """ROLE: "Human like robot browsing the web and observe agent."

        GOAL: "Analyse the current page elements and give your observation about the current page. And also whether our actions are making us to go near to the final goal or not, if not then reason and what can be done."

        BACKSTORY: "You are expert in deciding what to do next and analysing the current page elements.
        You always browse number of websites and visit different websites and observe what elements are present on the page and there work."
        """

        human = """DESCRIPTION: "Analyse the current page elements and give your observation.
        The current page URL is: {current_url} and the current page elements are:
        {current_page_elements}

        The final goal is: {final_goal}

        TAKEN ACTIONS SO FAR:
        {actions_taken}

        EXPECTED OUTPUT: "A very short, simple and precise observation paragraph from the current page elements that where we are and what could be our next step to achieve the final goal."
        """.format(current_page_elements=current_page_elements, current_url=current_url, final_goal=self.final_goal, actions_taken=get_actions_taken_with_thoughts(self.actions_taken))

        chat = []
        chat.append({
            "role": "system",
            "content": system
        })
        chat.append({
            "role": "user",
            "content": human
        })

        with open("observation_history.json", "w") as f:
            json.dump(chat, f, indent=4)

        self.history.extend(chat)  # Add chat to history

        chat_completion = self.client.chat.completions.create(
            messages=chat,
            model=self.available_model[1],
            temperature=1,
            stream=False,
            top_p=1,
            max_tokens=self.max_tokens,
            stop=None,
        )

        return chat_completion.choices[0].message.content

    def _next_action(self, objective, current_url, current_page_elements, error=None):
        system = """ROLE: "Human like robot browsing the web."

        GOAL: "Give next action with your thoughts needed to perform in browser."

        BACKSTORY: "You are expert in deciding what to do next.
        You always browse the web and visit different websites to perform some actions with logical thoughts.
        Your goal is to give an next capable, concise, simple and logical action and yout thoughts on it from user's objective, final goal, current page elements and past action with it thoughts,
        ensuring the objective is achieved with the help of browser."
        """

        with open("action_history.json", "w") as f:
            json.dump(self.history, f, indent=4)
        description_prompt = NEXT_STEP_ACTION_DESCRIPTION_PROMPT.format(
            objective=objective, final_goal=self.final_goal, actions_taken=get_actions_taken(self.actions_taken), observation=self.temp_objective, current_url=current_url, current_page_elements=current_page_elements, error=error)
        human = """{description_prompt}

        {NEXT_STEP_ACTION_GOAL_PROMPT}
        """.format(description_prompt=description_prompt, NEXT_STEP_ACTION_GOAL_PROMPT=NEXT_STEP_ACTION_GOAL_PROMPT)

        chat = []
        chat.append({
            "role": "system",
            "content": system
        })
        chat.append({
            "role": "user",
            "content": human
        })

        self.history.extend(chat)  # Add chat to history

        print("Chat completion start....")

        chat_completion = self.client.chat.completions.create(
            messages=chat,
            model=self.available_model[0],
            temperature=1,
            stream=False,
            top_p=1,
            stop=None,
            max_tokens=self.max_tokens,
            # Enable JSON mode by setting the response format
            response_format={"type": "json_object"},
        )

        print("Chat completion end....")

        response = chat_completion.choices[0].message.content
        json_response = parse_json_garbage(response)
        print("\nNEXT ACTION RESPONSE:\n")
        print(json.dumps(json_response, indent=4))
        print("\n")

        self.history.append(
            {
                "role": "assistant",
                "content": json_response
            }
        )  # Add assistant response to history
        self.actions_taken.append(json_response)

        return json_response
