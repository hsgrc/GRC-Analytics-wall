from app.knowledge_base import retrieve

TESTS = [
    "What membership plans are available?",
    "Tell me about membership benefits",
    "How does renewal work?",
    "tell me something about GRC",
    "How can I contact GetRightCover?",
    "What is the price of the 2 wheeler membership?",
]

for question in TESTS:
    context, sources = retrieve(question)
    print("=" * 70)
    print("QUESTION:", question)
    print("SOURCES :", sources)
    print("CONTEXT :\n", context)
