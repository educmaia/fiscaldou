import os
from dotenv import load_dotenv
from openai import OpenAI
from typing import List, Dict

load_dotenv()

client = None


def get_client():
    global client
    if client is None:
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            try:
                # Clear proxy environment variables to avoid issues
                proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY',
                              'http_proxy', 'https_proxy']
                saved_proxies = {}
                for var in proxy_vars:
                    if var in os.environ:
                        saved_proxies[var] = os.environ[var]
                        del os.environ[var]

                client = OpenAI(api_key=api_key)
                print("OpenAI client initialized successfully.")

                # Restore proxy variables
                for var, value in saved_proxies.items():
                    os.environ[var] = value

            except Exception as e:
                print(f"OpenAI client init error: {e}")
                client = None
        else:
            print("No OPENAI_API_KEY found. Using fallback summaries.")
            client = None
    return client


def generate_summary(match: Dict, use_ai: bool = True) -> str:
    """
    Generate an elaborated summary for a matching article using OpenAI.

    Args:
        match (Dict): Match dict with 'article', 'terms_matched', 'snippets'.
        use_ai (bool): Whether to use AI for summary. Defaults to True.

    Returns:
        str: Summary text (or fallback if API fails or disabled).
    """
    article_text = match['article']['text']
    terms = ', '.join(match['terms_matched'])

    if not use_ai:
        # Simple fallback summary
        fallback = f"Resumo simples: Encontrado em {match['article']['filename']} ({match['article']['section']}):\nTermos: {terms}\nTrechos: {'. '.join(match['snippets'][:3])}"
        return fallback

    client = get_client()
    if not client:
        # Fallback to simple summary using snippets
        fallback = f"Resumo simples: Encontrado em {match['article']['filename']} ({match['article']['section']}):\nTermos: {terms}\nTrechos: {'. '.join(match['snippets'][:3])}"
        return fallback

    try:
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um assistente especializado em resumos de publicações oficiais do DOU. Forneça um resumo conciso e objetivo em português, destacando a relevância dos termos mencionados."
                },
                {
                    "role": "user",
                    # Truncate to fit token limit
                    "content": f"Resuma o seguinte artigo do DOU, enfatizando menções aos termos '{terms}':\n\n{article_text[:4000]}"
                }
            ],
            max_tokens=300,
            temperature=0.3
        )
        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        print(f"OpenAI API error: {e}")
        # Fallback
        fallback = f"Resumo indisponível (erro API): Encontrado em {match['article']['filename']}.\nTermos: {terms}\nTrechos: {'. '.join(match['snippets'][:3])}"
        return fallback


def summarize_matches(matches: List[Dict], use_ai: bool = True) -> List[Dict]:
    """
    Generate summaries for all matches.

    Args:
        matches (List[Dict]): List of match dicts from search.
        use_ai (bool): Whether to use AI for summaries. Defaults to True.

    Returns:
        List[Dict]: Matches with added 'summary' key.
    """
    for match in matches:
        match['summary'] = generate_summary(match, use_ai=use_ai)
    return matches


if __name__ == "__main__":
    # Example usage
    from search import find_matches
    matches = find_matches()
    if matches:
        summarized = summarize_matches(matches)
        for match in summarized:
            print(
                f"Summary for {match['article']['filename']}:\n{match['summary']}\n---")
    else:
        print("No matches to summarize.")
