import pandas as pd
from openai import OpenAI
import os
import streamlit as st
import time

# Set your OpenAI API key
OPENAI_API_KEY = 'sk-proj-Mg8KiNNKLAlC9bNcqk1oT3BlbkFJ83Ha86GAIh7vVnvrhVPU'

client = OpenAI(
    # This is the default and can be omitted
    api_key=OPENAI_API_KEY
)

# Define sample queries for each intent and sub-intent
intent_samples = {
    "Status Intent": [
        "What’s the status of my Cash?",
        "Have I earned any Walmart Cash?",
        "Can you tell me if my Cash is pending?"
    ],
    "Discoverability Intent": {
        "Difficulty discovering earned Cash": [
            "How do I see the Cash I've earned?",
            "Show me my earned Cash."
        ],
        "Difficulty discovering items/offers with Cash": [
            "Which items have Cash?",
            "What offers can get me Cash?",
            "Can you list items with Cash offers?"
        ]
    },
    "Usability Intent": [
        "How can I use/redeem my Cash?",
        "What can I use my Walmart Cash for?",
        "Tell me how to redeem my Cash."
    ],
    "FAQ Intent": [
        "What is Cash?",
        "How can I earn Cash?",
        "Explain Walmart Cash to me."
    ]
}


def handle_status_intent(custid, orderid):
    response = get_cash_status(custid, orderid)
    return response

def handle_discoverability_intent(subintent, customer_id, order_id):
    # Further classify the discoverability intent
    
    if subintent == "Difficulty discovering earned Cash":
        cash_status = get_cash_status(customer_id, order_id)
        return f"I understnad that you're having {subintent}.<br>Your balance can be found here : 'https://www.walmart.com/rewards-history' <br>{cash_status}"
    elif subintent == "Difficulty discovering items/offers with Cash":
        return f"I understnad that you're having {subintent}"
    else:
        return "Discoverability intent not recognized."
        

def handle_usability_intent(query):
    return "This is a response for Usability Intent."

def handle_faq_intent(query):
    return "This is a response for FAQ Intent."




def create_classification_prompt(query, intent_samples):
    prompt = f"Classify the intent and sub-intents of the following query: '{query}' into one of the following intents and sub-intents:\n\n"
    
    for intent, examples in intent_samples.items():
        prompt += f"{intent}:\n"
        if isinstance(examples, list):
            for example in examples:
                prompt += f"   - {example}\n"
        elif isinstance(examples, dict):
            for sub_intent, sub_examples in examples.items():
                prompt += f"   Sub-intents:\n"
                prompt += f"   {sub_intent}\n"
                for sub_example in sub_examples:
                    prompt += f"      - {sub_example}\n"
        prompt += "\n"
    
    prompt += "Classify the query accurately based on these examples."
    return prompt

def classify_intent_and_sub_intent(query):
    prompt = create_classification_prompt(query, intent_samples)
    context = """To earn Cash, users should clip a Cash eligible item within the clip eligible window, must meet the Must buy X criteria, and make a purchase within the redeem date. THe order must be delivered, else the Cash will be in pending state. If the order is canceled/returned, the user is not eligible to earn cash. If the user has done everything to earn cash, but still cash wasn’t earned within 3 days of having order delivery, then escalate to Customer support. 
    """
    response = client.with_options(max_retries=5).chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": f"You are an assistant that classifies customer queries into specific intents and sub-intents.{context}"},
            {"role": "user", "content": prompt}
        ]
    )
    
    message_content = response.choices[0].message.content.strip()
    
    # Extract intent and sub-intent
    intent = None
    sub_intent = None

    # Extract intent and sub-intent by searching for matches in intent_samples
    for intent_key, examples in intent_samples.items():
        if intent_key in message_content:
            intent = intent_key
            if isinstance(examples, dict):
                for sub_intent_key in examples:
                    if sub_intent_key in message_content:
                        sub_intent = sub_intent_key
                        break
            break
    
    return {'intent': intent, 'sub_intent': sub_intent}


def chatbot(query, custid, orderid):
    response = classify_intent_and_sub_intent(query)
    intent, subintent = response["intent"], response["sub_intent"]
    
    if intent == "Status Intent":
        response = handle_status_intent(custid, orderid)
    elif intent == "Discoverability Intent":
        response = handle_discoverability_intent(subintent, custid, orderid)
    elif intent == "Usability Intent":
        response = handle_usability_intent(query)
    elif intent == "FAQ Intent":
        response = handle_faq_intent(query)
    else:
        response = "I'm sorry, I didn't understand your query."

    return response



def get_cash_status(customer_id, order_id):
    # Find the specific order for the customer
    order = df[(df['CustomerId'] == customer_id) & (df['OrderId'] == order_id)]
    if order.empty:
        return "Order not found."

    order = order.iloc[0]

    # Check the eligibility and status conditions
    if not order['EligibleForCash']:
        return "The items in this order are not eligible for Walmart Cash."

    if not order['ClipMade']:
        return "You did not clip the eligible items for Walmart Cash."

    if not order['MustBuyCriteriaMet']:
        return "The Must Buy criteria were not met for this order."

    if not order['PurchaseWithinRedeemWindow']:
        return "The purchase was not made within the redeem window."

    if order['OrderStatus'] in ['Canceled', 'Returned', 'Substituted', 'Unavailable']:
        return f"The order was {order['OrderStatus']}, so you are not eligible for Walmart Cash."

    if order['OrderStatus'] == 'Pending':
        return "The order is still pending. Your Walmart Cash will be processed once the order is delivered."

    if order['CashEarned'] > 0:
        return f"You have earned ${order['CashEarned']} Walmart Cash on {order['CashEarnedDate']}."

    return "There was an issue with earning Walmart Cash. Please contact customer support if it has been more than 3 days since delivery."



# Create a dummy dataset
data = {
    'CustomerId': [1, 2, 3, 4],
    'OrderId': [101, 102, 103, 104],
    'OrderDate': ['2024-06-01', '2024-06-02', '2024-06-03', '2024-06-04'],
    'OrderAmount': [100, 150, 200, 250],
    'ItemsPurchased': [['item1', 'item2'], ['item3'], ['item4', 'item5'], ['item6']],
    'EligibleForCash': [True, True, True, True],
    'ClipMade': [True, True, False, True],
    'MustBuyCriteriaMet': [True, True, False, False],
    'PurchaseWithinRedeemWindow': [True, True, False, True],
    'OrderStatus': ['Delivered', 'Pending', 'Delivered', 'Returned'],
    'CashEarned': [10, 0, 0, 0],
    'CashEarnedDate': ['2024-06-04', None, None, None]
}

df = pd.DataFrame(data)


def display_typing_animation(text, delay=0.02):
    words = text.split()
    text_container = st.empty()  # Create an empty container
    for i in range(len(words) + 1):
        #text_container.text(" ".join(words[:i]))  # Update the container with the text

        wrapped_text = "Walmart Assistant:\n" + " ".join(words[:i]).replace('.', '<br>')
        text_container.markdown(f'<div style="word-wrap: break-word;">{wrapped_text}</div>', unsafe_allow_html=True)
        
        time.sleep(delay)
        
query_text = ""
# Streamlit app
st.title('Walmart Cash Chatbot')
st.text('Hi! Welcome! Ask anything about Cash')
st.dataframe(df)

userid = st.text_input('User ID')
orderid = st.text_input('Order ID')
query = st.chat_input('Enter your query')


if userid and orderid and query:
    query_text += f"User: {query}\n"
    with st.spinner("Processing..."):
        userid = int(userid)
        orderid = int(orderid)
        response = chatbot(query, userid, orderid)
        st.empty()  # Clear the spinner
        st.text(query_text)
        display_typing_animation(response)
