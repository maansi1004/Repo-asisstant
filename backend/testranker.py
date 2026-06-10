
from reranker import rerank
chunks = [
    {'text': 'def login(user, password): verify credentials', 'metadata': {'filepath': 'auth.py', 'func_name': 'login', 'language': 'python'}},
    {'text': 'def get_profile(user_id): return user data', 'metadata': {'filepath': 'user.py', 'func_name': 'get_profile', 'language': 'python'}},
    {'text': 'def logout(user): clear session', 'metadata': {'filepath': 'auth.py', 'func_name': 'logout', 'language': 'python'}},
]
results = rerank('how does login work', chunks, top_k=2)
for r in results:
    print(r['metadata']['func_name'], '→ score:', r['reranker_score'])
