import re
import wikipedia
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.document_loaders import PyPDFLoader

class ChatAssistant:
    def __init__(self):
        wikipedia.set_lang("en")
        self.embeddings = OpenAIEmbeddings()
        self.store      = None
        self.docs       = []

    def add_pdf(self, path: str):
        loader    = PyPDFLoader(path)
        self.docs = loader.load()
        try:
            self.store = FAISS.from_documents(self.docs, self.embeddings)
        except Exception as e:
            msg = str(e).lower()
            if "quota" in msg or "insufficient_quota" in msg:
                print("⚠️ Skipping embeddings due to OpenAI quota.")
                self.store = None
            else:
                raise

    def _clean_query(self, question: str) -> str:
        # strip leading question words and trailing punctuation
        q = question.strip()
        q = re.sub(r'^(what|who|where|when|why|how)\s+(is|are|do|does)\s+', '', q, flags=re.IGNORECASE)
        q = re.sub(r'[?!.]+$', '', q).strip()
        return q

    def answer(self, question: str, lang: str = "en-US") -> dict:
        # 1) Clean up the user’s question for Wikipedia
        term = self._clean_query(question)
        wiki_lang = lang.split("-")[0]
        wikipedia.set_lang(wiki_lang)

        # 2) Always fetch a two-sentence Wikipedia summary + link
        try:
            pages = wikipedia.search(term, results=1)
            if pages:
                title   = pages[0]
                summary = wikipedia.summary(title, sentences=2, auto_suggest=False)
                try:
                    url = wikipedia.page(title, auto_suggest=False).url
                except:
                    url = f"https://{wiki_lang}.wikipedia.org/wiki/{title.replace(' ', '_')}"
            else:
                summary = f"No Wikipedia entry found for “{term}.”"
                url     = ""
        except Exception:
            summary = "Wikipedia lookup failed."
            url     = ""

        wiki_html = (
            f"<strong>Wikipedia:</strong> {summary} "
            f"<a href=\"{url}\" target=\"_blank\">Read more</a>"
        )

        # 3) If a PDF was loaded, pull a 200-char window around the term
        context = ""
        if self.docs:
            full_text = " ".join(doc.page_content for doc in self.docs)
            m = re.search(re.escape(term), full_text, re.IGNORECASE)
            if m:
                start   = max(m.start() - 100, 0)
                end     = min(m.end()   + 100, len(full_text))
                context = full_text[start:end].strip()
            if not context:
                context = f"No matching text found in your PDF for “{term}.”"

        # 4) Return all three keys—context may be empty if no PDF
        return {
            "context" : context,
            "wiki_html": wiki_html,
            "wiki_url": url
        }
    