from groq import Groq
import os

def health_care_query(prompt):
    client = Groq(api_key=os.environ.get('GROQ_API_KEY'))
    completion = client.chat.completions.create(
        model='llama-3.1-8b-instant',
        messages=[
            {'role': 'system', 'content': 'one line qna'},
            {'role': 'user', 'content': prompt}
        ],
        stream=True,
        stop=None,
        top_p=1,
        max_tokens=1024,
    )
    result = ''
    for chunk in completion:
        result += chunk.choices[0].delta.content or " "
    return result
    
