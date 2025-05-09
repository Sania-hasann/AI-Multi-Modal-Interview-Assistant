import spacy
from textblob import TextBlob
from gensim import corpora, models
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Load Spacy's English tokenizer, tagger, parser, NER, and word vectors
nlp = spacy.load("en_core_web_sm")
nltk.data.path.append("C:/Users/LENOVO/Documents/FYP/audio-llm-SER/Fyp/lib/nltk_data")
# Ensure nltk resources are downloaded
nltk.download('stopwords')
nltk.download('punkt_tab', force=True, download_dir='C:/Users/LENOVO/Documents/FYP/audio-llm-SER/Fyp/lib/nltk_data')


# Stop words list
stop_words = set(stopwords.words('english'))

def parse_transcription(text):
    # Using Spacy for dependency parsing
    doc = nlp(text)
    parsed_data = {token.text: {"dependency": token.dep_, "head": token.head.text} for token in doc}
    return parsed_data

def extract_topics(text):
    # Prepare text for topic modeling
    words = word_tokenize(text.lower())
    words = [word for word in words if word not in stop_words and word.isalnum()]
    
    # Create a dictionary and corpus for topic modeling
    dictionary = corpora.Dictionary([words])
    corpus = [dictionary.doc2bow(words)]
    
    # Applying Latent Dirichlet Allocation (LDA) model from Gensim
    lda_model = models.LdaModel(corpus, num_topics=1, id2word=dictionary, passes=15)
    topics = lda_model.print_topics(num_words=3)
    return [topic[1] for topic in topics]

def sentiment_score(text):
    # Using TextBlob for sentiment analysis
    analysis = TextBlob(text)
    # Return the sentiment as a formatted string
    return f"Sentiment: {analysis.sentiment.polarity:.2f} (polarity), {analysis.sentiment.subjectivity:.2f} (subjectivity)"
