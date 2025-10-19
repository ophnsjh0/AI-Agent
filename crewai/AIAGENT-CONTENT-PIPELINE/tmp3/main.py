import os
from datetime import datetime
from zoneinfo import ZoneInfo
from dataclasses import is_dataclass, asdict
from typing import List
from crewai.flow.flow import Flow, listen, start, router, and_, or_
from crewai.agent import Agent
from crewai import LLM
from pydantic import BaseModel
from tools import web_search_tool
from seo_crew import SeoCrew
from virality_crew import ViralityCrew


def _now_kst_str(fmt="%Y%m%d-%H%M%S"):
    return datetime.now(ZoneInfo("Asia/Seoul")).strftime(fmt)

def _to_dict(obj):
    """Tweet/LinkedIn/Blog 객체를 dict로 안전 변환"""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, BaseModel):
        dump = getattr(obj, "model_dump", None)
        if callable(dump):
            return dump()
        dump = getattr(obj, "dict", None)  # pydantic v1
        if callable(dump):
            return dump()
    if is_dataclass(obj):
        return asdict(obj)
    # 문자열 등은 value에 담아서 반환
    if isinstance(obj, (str, int, float, bool)):
        return {"value": obj}
    return {"value": str(obj)}

def _score_value(state):
    """self.state.score.score 형태를 안전하게 꺼냄"""
    score = getattr(getattr(state, "score", None), "score", None)
    if score is None and isinstance(getattr(state, "score", None), dict):
        score = state.score.get("score")
    return score

def _build_markdown(content_type: str, payload, state) -> str:
    """content_type과 payload로 마크다운 본문 생성"""
    d = _to_dict(payload)
    ts_human = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S KST")
    score = _score_value(state)

    lines = []
    lines.append(f"<!-- generated: {ts_human} -->")
    lines.append(f"**Type:** {content_type}")
    if score is not None:
        lines.append(f"**Score:** {score}/100")
    lines.append("---")

    ct = content_type.lower()
    if ct == "tweet":
        text = d.get("text") or d.get("value") or str(payload)
        lines.append(text)

    elif ct == "linkedin":
        title = d.get("title") or "Untitled"
        body  = d.get("body") or d.get("content") or d.get("value") or ""
        lines.append(f"# {title}")
        if body:
            lines.append("")
            lines.append(body)

    elif ct == "blog":
        title    = d.get("title") or "Untitled"
        subtitle = d.get("subtitle") or ""
        sections = d.get("sections") or []
        lines.append(f"# {title}")
        if subtitle:
            lines.append("")
            lines.append(f"> {subtitle}")
        if sections:
            # sections가 문자열 리스트라고 가정. 아니면 str()로 안전 처리
            lines.append("")
            for s in sections:
                lines.append(f"## {s if isinstance(s, str) else str(s)}")

        # 본문/content 필드가 있다면 덧붙이기
        body = d.get("body") or d.get("content")
        if body:
            lines.append("")
            lines.append(str(body))

    else:
        # 미정의 타입은 전체 dict를 코드블록으로 남김
        lines.append("```json")
        import json
        lines.append(json.dumps(d, ensure_ascii=False, indent=2))
        lines.append("```")

    return "\n".join(lines)

def _save_markdown(content_type: str, markdown_text: str, output_dir="output") -> str:
    # 상대경로로 지정 → 현재 프로젝트 디렉터리 내부에 output 폴더 생성
    os.makedirs(output_dir, exist_ok=True)
    ts = _now_kst_str("%Y%m%d-%H%M%S")
    filename = f"{ts}-{content_type}.md"
    path = os.path.join(output_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(markdown_text)
    return path


class BlogPost(BaseModel):
    title: str
    subtitle: str
    sections: List[str]


class Tweet(BaseModel):
    content: str
    hashtags: str


class LinkedInPost(BaseModel):
    hook: str
    content: str
    call_to_action: str


class Score(BaseModel):
    score: int = 0
    reason: str = ""

class ContentPipeLineState(BaseModel):
    
    #Input
    content_type: str = ""
    topic: str = ""
    
    #Internal 
    max_length: int = 0
    research: str = ""
    score: Score | None = None
    
    #Content
    blog_post: BlogPost | None = None
    tweet: Tweet | None = None
    linkedin_post: LinkedInPost | None = None

class ContentPipeLineFlow(Flow[ContentPipeLineState]):
    
    @start()
    def init_content_pipeline(self):
        if self.state.content_type not in ["blog", "tweet", "linkedin"]:
            raise ValueError("The content type is wrong.")
        
        if self.state.topic == "":
            raise ValueError("The topic can,t be blank.")
        
        if self.state.content_type == "tweet":
            self.state.max_length = 150
        elif self.state.content_type == "blog":
            self.state.max_length = 800
        elif self.state.content_type == "linkedin":
            self.state.max_length = 500
    
    @listen(init_content_pipeline)
    def conduct_research(self):

        researcher = Agent(
            role="Head Researcher",
            backstory="You're like a digital detective who loves digging up fascinating facts and insights. You have a knack for finding the good stuff that others miss.",
            goal=f"Find the most interesting and useful info about {self.state.topic}",
            tools=[web_search_tool],
        )
        
        self.state.research = researcher.kickoff(
            f"Find the most interesting and useful info about {self.state.topic}"
        )
        
    
    @router(conduct_research)
    def conduct_research_router(self):
        content_type = self.state.content_type
        
        if content_type == "blog":
            return "make_blog"
        elif content_type == "tweet":
            return "make_tweet"
        else:
            return "make_linkedin_post"
    
    @listen(or_("make_blog", "remake_blog"))
    def handle_make_blog(self):
        blog_post = self.state.blog_post
        
        llm = LLM( model="openai/o4-mini", response_format=BlogPost )
        
        if blog_post is None:
            print("making blog.")
            result = llm.call(
                f"""
            Make a blog post on the topic {self.state.topic} using the following research:

            <research>
            ================
            {self.state.research}
            ================
            </research>
            """
            )
        else:
            print("Remaking blog.")
            result = llm.call(
                f"""
            You wrote this blog post on {self.state.topic}, but it does not have a good SEO score because of {self.state.score.reason} 
            
            Improve it.

            <blog post>
            {self.state.blog_post.model_dump_json()}
            </blog post>

            Use the following research.

            <research>
            ================
            {self.state.research}
            ================
            </research>
            """
            )
        
        self.state.blog_post = BlogPost.model_validate_json(result)
        
    @listen(or_("make_tweet", "remake_tweet"))
    def handle_make_tweet(self):
        tweet = self.state.tweet

        llm = LLM(model="openai/o4-mini", response_format=Tweet)

        if tweet is None:
            print("making tweet.")
            result = llm.call(
                f"""
            Make a tweet that can go viral on the topic {self.state.topic} using the following research:

            <research>
            ================
            {self.state.research}
            ================
            </research>
            """
            )
        else:
            print("remaking tweet.")
            result = llm.call(
                f"""
            You wrote this tweet on {self.state.topic}, but it does not have a good virality score because of {self.state.score.reason} 
            
            Improve it.

            <tweet>
            {self.state.tweet.model_dump_json()}
            </tweet>

            Use the following research.

            <research>
            ================
            {self.state.research}
            ================
            </research>
            """
            )

        self.state.tweet = Tweet.model_validate_json(result)
        
    @listen(or_("make_linkedin_post", "remake_linkedin_post"))
    def handle_make_linkedin_post(self):
        linkedin_post = self.state.linkedin_post

        llm = LLM(model="openai/o4-mini", response_format=LinkedInPost)

        if linkedin_post is None:
            print("making linkedin_post.")
            result = llm.call(
                f"""
            Make a linkedin post that can go viral on the topic {self.state.topic} using the following research:

            <research>
            ================
            {self.state.research}
            ================
            </research>
            """
            )
        else:
            print("remaking linkedin_post.")
            result = llm.call(
                f"""
            You wrote this linkedin post on {self.state.topic}, but it does not have a good virality score because of {self.state.score.reason} 
            
            Improve it.

            <linkedin_post>
            {self.state.linkedin_post.model_dump_json()}
            </linkedin_post>

            Use the following research.

            <research>
            ================
            {self.state.research}
            ================
            </research>
            """
            )

        self.state.linkedin_post = LinkedInPost.model_validate_json(result)

        
    @listen(handle_make_blog)
    def check_seo(self):
        
        result = SeoCrew().crew().kickoff(
            inputs={
                "topic" : self.state.topic,
                "blog_post" : self.state.blog_post.model_dump_json()
            }
        )
        self.state.score = result.pydantic 
        
    @listen(or_(handle_make_tweet, handle_make_linkedin_post))
    def check_viality(self):
        result = (
            ViralityCrew()
            .crew()
            .kickoff(
                inputs={
                    "topic": self.state.topic,
                    "content_type": self.state.content_type,
                    "content": (
                        self.state.tweet.model_dump_json() 
                        if self.state.content_type == "tweet"
                        else self.state.linkedin_post.model_dump_json()
                    ),
                }
            )
        )
        self.state.score = result.pydantic
        
    @router(or_(check_seo, check_viality))
    def score_router(self):
        content_type = self.state.content_type 
        score = self.state.score
        
        if score.score >= 7:
            return "check_passed"
        else:
            if content_type == "blog":
                return "remake_blog"
            elif content_type == "tweet":
                return "remake_tweet"
            elif content_type == "linkedin":
                return "remake_linkedin_post"
            
    @listen("check_passed")
    def finalize_content(self):
        """Finalize the content"""
        print("🎉 Finalizing content...")

        ct = self.state.content_type  # blog / tweet / linkedin

        if ct == "blog":
            print(f"📝 Blog Post: {self.state.blog_post.title}")
            print(f"🔍 SEO Score: {self.state.score.score}/100")
            payload = self.state.blog_post
        elif ct == "tweet":
            print(f"🐦 Tweet: {self.state.tweet}")
            print(f"🚀 Virality Score: {self.state.score.score}/100")
            payload = self.state.tweet
        elif ct == "linkedin":
            print(f"💼 LinkedIn: {self.state.linkedin_post.title}")
            print(f"🚀 Virality Score: {self.state.score.score}/100")
            payload = self.state.linkedin_post
        else:
            # 혹시 모를 타입 확장 대비
            payload = getattr(self.state, ct, None)

        # 👉 여기서 파일로 저장
        md = _build_markdown(ct, payload, self.state)
        saved_path = _save_markdown(ct, md, output_dir="output")
        print(f"💾 Saved: {saved_path}")

        print("✅ Content ready for publication!")

        # 원래의 반환 로직 유지
        return (
            self.state.linkedin_post
            if ct == "linkedin"
            else (self.state.tweet if ct == "tweet" else self.state.blog_post)
        )

        
flow = ContentPipeLineFlow()

#flow.plot()

flow.kickoff(
    inputs={
        "content_type": "tweet",
        "topic": "AI Dog Training",
    }
)
