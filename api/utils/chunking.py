from langchain.text_splitter import RecursiveCharacterTextSplitter

""" Utility for splitting large text documents into manageable chunks """

# Configure recursive splitter with overlaps to maintain context
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=512, chunk_overlap=50, separators=["\n\n", "\n", " ", ""]
)


# Split input text into chunks based on configuration
def chunk_text(text: str):
    return text_splitter.split_text(text)
