# The Unofficial Guide — Project 1

> This is my first project for the CodePath AI201 course. I built a simple RAG-based chatbot that provides you with information about different events in the Bryan/College Station area. I designed a planning guide that helped me implement each feature one-by-one, including building a webscraper, chunking data, vectorizing it, giving it to an LLM,and then retrieving it for a coherent output.

---

## Domain

<!-- What topic or category of knowledge does your system cover?
     Why is this knowledge valuable, and why is it hard to find through official channels?
     Example: "Student reviews of CS professors at [university] — useful because official
     course descriptions don't reflect teaching style, exam difficulty, or workload." -->
This chatbot provides the user with help on finding things to do in the Bryan/College staiton area. 

---

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 |Reddit|A thread of places in Bryan/College Station that students recommend. |https://www.reddit.com/r/aggies/comments/13znhx2/what_are_some_things_to_doplaces_to_go_in_bryan/ |
| 2 |Reddit |A thread of things to do in Bryan specifically |https://www.reddit.com/r/aggies/comments/1clpu1l/is_there_anything_to_do_in_bryan/ |
| 3 |Destination Bryan |Official website of Bryan, Texas detailing the things to do there |destinationbryan.com/things-to-do/ |
| 4 |Visit College Station |Official website of College Station, Texas detailing the things to do there |https://visit.cstx.gov/things-to-do/ |
| 5 |TripAdvisor |List of things to do in the Bryan area |https://www.tripadvisor.com/Attractions-g55543-Activities-Bryan_Texas.html |
| 6 |Texas A&M University |Official University Calendar of events |https://getinvolved.tamu.edu/events|
| 7 |Reddit |Thread detailing nightlife in College Station |https://www.reddit.com/r/CollegeStation/comments/1iryy2y/night_life/ |
| 8 | Visit College Station|Official College Station website detailing nightlife options there |https://visit.cstx.gov/things-to-do/nightlife/ |
| 9 |Visit College Station |Official College Station events calendar |https://visit.cstx.gov/events/ |
| 10 |Destination Bryan |Official Bryan events calendar |https://www.destinationbryan.com/events/ |


FULL DISCLOSURE: I was not able to webscrape Reddit and TripAdvisor. I ommitted those websites, but am still keeping them here.
---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->


**Chunk size:**
A target of 80 tokens with a hard cap of 256 tokens. "Tokens" are counted with the all-MiniLM-L6-v2 tokenizer (`transformers.AutoTokenizer`), so the count is exactly what the embedding model sees. Each cleaned document is split into paragraphs. Any paragraph longer than the target is further split on sentence boundaries.

**Overlap:**
No overlap. All of the documents that survived scraping are event calendars and attraction/venue lists where each item is self-contained, so carrying text across boundaries would just duplicate one venue into a neighbor's chunk and blur retrieval. (Overlap would matter for the planned Reddit discussion threads, where an idea spans several sentences, but those sources were blocked by anti-bot protection and are not in the corpus.)

**Why these choices fit your documents:**
The 256 token cap is the model's limit, and a single attraction or event is short. Small chunks keep one or two items per vector, which sharpens retrieval precision for specific queries (e.g. "live music in downtown Bryan") instead of returning a paragraph where the relevant line is diluted.

**Preprocessing before chunking:**
- HTML stripped with BeautifulSoup (lxml): removed `script/style/noscript/nav/footer/header/form/svg/iframe/aside`, then extracted text from the `main`/`article`/`body` container.
- Encoding fixed by parsing the raw response bytes so BeautifulSoup detects each page's own charset (some sites otherwise produced mojibake like `cafés`/`â€¦`).
- Whitespace normalized
- Boilerplate removed with a filter that drops nav/call-to-action junk lines ("Details", "Map", "Save", "Open in Google Maps", "Learn More", "Continue Reading", "Submit Your Event", "Results 1-12 of …", e-newsletter prompts) 

**Final chunk count:**
50 chunks across 6 documents. Chunk sizes range 25–80 tokens (avg ~67), all within the 256-token model limit.

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:**
Llama-3.3-70b-versatile
**Production tradeoff reflection:**
The model used is a very baseline free model available on Groq. It has extremely fast response times(because of the Groq LPU vs traditional GPU hardware). However, there is a loss of reasoning accuracy due to running this heavily quantized version of the model to prioritize speed. Furthermore, to make it remember context I need to add code to store the chat history and handle the memory myself.
---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->
I crafted a strong prompt that restricts the LLM from pulling from any outside sources. If it does not have enough information to answer a question, it will simply say that.

**System prompt grounding instruction:**
"""You are "The Unofficial Guide," a local expert on things to do \
and events in Bryan and College Station, Texas.

Answer the user's question using ONLY the information in the numbered context \
passages provided below. Follow these rules strictly:

1. Use no prior knowledge and add no facts that are not in the context. If the \
context does not contain enough information to answer, reply exactly: \
"I don't have enough information in my sources to answer that." Do not guess or \
fill gaps from general knowledge.
2. After each claim, cite the passage number(s) it came from in square brackets, \
e.g. "Northgate has many bars [2]." Cite multiple passages as [1][3] when relevant.
3. Be concise and specific — name the actual places, events, dates, or addresses \
that appear in the context.
4. Finish with a line that starts with "Sources:" listing the passage numbers you \
actually used (e.g. "Sources: [1], [2]")."""

**How source attribution is surfaced in the response:**
NO_CONTEXT_MSG = "I don't have enough information in my sources to answer that."
---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What nightlife is present in College Station?| College Station's historic Northgate district presents many nightlife opportunities.|College Station offers a nightlife experience that will fit any mood, with options for a relaxing night out with wine or dancing the night away [2]. The Historic Northgate District is a part of this nightlife scene, where entertainment, dining, and Aggie traditions collide [10]. Whether you're looking for a relaxing night out or want to dance, College Station has a nightlife experience [2]. |Relevant |Accurate |
| 2 |Are there any scenic nature spots in Bryan? |Lake Bryan presents a beautiful scenic backdrop with restaurants and picturesque waters. |There is a mention of a place called Aggieland Safari [11], and Lake Walk is also mentioned as a location for live concerts [1][2]. Additionally, Midtown Park is mentioned as a location for events [6][12]. However, it is not explicitly stated that these are scenic nature spots. Sources: [1], [2], [6], [11], [12]

 |Relevant |Partially accurate |
| 3 |Is there anything in College Station for a history buff? |College Station boasts the George H.W. Bush Presidential Library and Museum and the Museum of the American G.I. |Yes, there are several attractions in College Station that would be of interest to a history buff, including the George H.W. Bush Presidential Library and Museum [1][3][6], and the Museum of the American G.I. [3][11]. Additionally, the city has a rich history and culture scene, with many historic landmarks and traditions [1][7][9]. The Carnegie History Center in nearby Bryan also offers historic experiences, such as the America 250 Scavenger Hunt [11]. |Relevant |Accurate |
| 4 |Where to exercise in College Station? |The A&M Campus has various Rec Centers. |To exercise in College Station, you can visit the city's outdoor spaces, which include scenic trails and parks [1]. The city also has sports venues [3][5] and trails [11] where you can engage in physical activities. Additionally, the Gary Halter Nature Center [7] and Wolf Pen Creek [7] may offer opportunities for outdoor exercise. |Relevant |Accurate| 5 | Are there any organic food markets in College Station?|Yes, the Aggieland Farmers Market is open on these days. |I don't have enough information in my sources to answer that. |Off-target |Inaccurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**
Are there any organic food markets in College Station?
**What the system returned:**
I don't have enough information in my sources to answer that
**Root cause (tied to a specific pipeline stage):**
I don't think my web scraping was able to get this information.
**What you would change to fix it:**
Scrape a lot more sites so my chatbot can pull from more chunks.
---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**
The spec greatly helped me during implementation. It gave me a strong guide on what I should be looking at doing, and each step I needed to take.
**One way your implementation diverged from the spec, and why:**
My implementation decided to use a lot less tokens per chunk. This is because the suggested token per chunk in the planning document was just way too much, which was verified during testing.

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:*
- *What it produced:*
- *What I changed or overrode:*
I gave Claude the websites I had and asked it what the most efficient way to scrape them would be. It told me that scraping reddit and tripadvisor would not be possible, but we were able to develop a scraper that extracted information from the other sites.
**Instance 2**

- *What I gave the AI:*
- *What it produced:*
- *What I changed or overrode:*
Claude helped me generate a simple user interface using streamlit to test my project.