import os
import json
from dotenv import load_dotenv
from crewai import Agent, Task, Crew
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from helpers import parse_json_garbage
from agent.prompt import FIRST_STEP_ACTION_DESCRIPTION_PROMPT, FIRST_STEP_ACTION_GOAL_PROMPT, NEXT_STEP_ACTION_DESCRIPTION_PROMPT, NEXT_STEP_ACTION_GOAL_PROMPT

load_dotenv()


class PragyaGPT:
    def __init__(self, model=None):
        self.available_model = ['llama3-8b-8192',
                                'mixtral-8x7b-32768', 'gemma-7b-it']
        self.llm = ChatGroq(
            temperature=0,
            groq_api_key=os.environ.get("GROQ_API_KEY"),
            model_name=model if model else self.available_model[0]
        )
        self.history = []
        self.temp_objective: str = None
        self.final_goal: str = None

        self.final_goal_agent = Agent(
            role="Final_Goal_Decider_Agent",
            goal="""clarify the final goal that user wants to solve, 
            finish the objective with there requirements and at the end after the goal is achieved give an answer to the user's objective(question).""",
            backstory="""You are an expert in deciding the final goal of user's objective. 
            Your goal is to give an final goal with the help of user's objective ensuring the objective is achieved with the help of browser.
            """,
            verbose=True,
            allow_delegation=True,
            llm=self.llm,
        )

        self.observer_agent = Agent(
            role="Human like robot browsing the web and observe agent",
            goal="""Analyse the current page elements and give your observationa about the current page. And also whether our actions are making us to go near to the final goal or not, if not then reason and what can be done.
            """,
            backstory="""You are expert in deciding what to do next and analysing the current page elements.
            You always browse number of websites and visit different websites and observe what elements are present on the page and there work.
            """,
            verbose=True,
            allow_delegation=True,
            llm=self.llm
        )

        self.driver_agent = Agent(
            role="Human like robot browsing the web",
            goal="""Give next action with your thoughts needed to perform in browser.
            """,
            # REMEMBER:
            # 1. You should provide thoughts and reasoning for your action.
            # 2. Your final response or answer should be in JSON format. If asked again just provide the same JSON again you resposed just before.
            backstory="""You are expert in deciding what to do next. 
            You always browse the web and visit different websites to perform some actions with logical thoughts.
            Your goal is to give an next capable, concise, simple and logical action and yout thoughts on it from user's objective, final goal, current page elements and past action with it thoughts,
            ensuring the objective is achieved with the help of browser.
            """,
            verbose=True,
            allow_delegation=True,
            llm=self.llm
        )

    def get_final_goal(self, objective):
        goal = Task(
            description="""What will be the final goal for the user's objective?
            {objective}""".format(objective=objective),
            expected_output="""A short, simple and precise goal that user wants to achieve with the help of browser.""",
            agent=self.final_goal_agent,
        )

        crew = Crew(
            agents=[self.final_goal_agent],
            tasks=[goal],
            verbose=2
        )

        result = crew.kickoff()
        self.final_goal = result

        return result # final goal
    
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
        """
        description_prompt = FIRST_STEP_ACTION_DESCRIPTION_PROMPT.format(objective=objective, final_goal=self.final_goal, error=error)
        print(description_prompt)

        prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
        chain = prompt | self.llm

        response = chain.invoke({"description_prompt": description_prompt, "FIRST_STEP_ACTION_GOAL_PROMPT": FIRST_STEP_ACTION_GOAL_PROMPT}).content
        json_response = parse_json_garbage(response)
        print(json.dumps(json_response, indent=4))

        self.history.append(response)

        return json_response
    
    def _observation(self, current_url, current_page_elements):
        observation_task = Task(
            description="""Analyse the current page elements and give your observation. 
            The current page URL is: {current_url} and the current page elements are:
            {current_page_elements}

            The final goal is: {final_goal}
            """.format(current_page_elements=current_page_elements, current_url=current_url, final_goal=self.final_goal),
            expected_output="""A short, simple and precise observation from the current page elements that where we are and what could be our next step to achieve the final goal.""",
            agent=self.driver_agent,
        )

        crew = Crew(
            agents=[self.observer_agent],
            tasks=[observation_task],
            verbose=2
        )

        result = crew.kickoff()
        self.temp_objective = result

        return result
    
    def _next_action(self, objective, current_url, current_page_elements, error=None):
        system = """ROLE: "Human like robot browsing the web."

        GOAL: "Give next action with your thoughts needed to perform in browser."

        BACKSTORY: "You are expert in deciding what to do next.
        You always browse the web and visit different websites to perform some actions with logical thoughts.
        Your goal is to give an next capable, concise, simple and logical action and yout thoughts on it from user's objective, final goal, current page elements and past action with it thoughts,
        ensuring the objective is achieved with the help of browser."
        """
        human = """{description_prompt}

        {NEXT_STEP_ACTION_GOAL_PROMPT}
        """

        description_prompt = NEXT_STEP_ACTION_DESCRIPTION_PROMPT.format(objective=objective, final_goal=self.final_goal, actions_taken=self.history, observation=self.temp_objective, current_url=current_url, current_page_elements=current_page_elements, error=error)
        print(description_prompt)

        prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
        chain = prompt | self.llm

        response = chain.invoke({"description_prompt": description_prompt, "NEXT_STEP_ACTION_GOAL_PROMPT": NEXT_STEP_ACTION_GOAL_PROMPT}).content
        json_response = parse_json_garbage(response)
        print(json.dumps(json_response, indent=4))

        self.history.append(response)

        return json_response
    
    def get_next_action(self, objective, current_page_elements, past_actions):
        action_task = Task(
            description="""What will be the next action for the user's objective?
            {objective}""".format(objective=objective),
            expected_output="""A short, simple and precise action that user wants to perform with the help of browser.""",
            agent=self.driver_agent,
        )

        crew = Crew(
            agents=[self.driver_agent],
            tasks=[action_task],
            verbose=2
        )

        result = crew.kickoff()
        return result
