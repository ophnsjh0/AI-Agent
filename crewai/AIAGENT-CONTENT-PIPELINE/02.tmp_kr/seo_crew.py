from crewai.project import CrewBase, agent, task, crew
from crewai import Agent, Task, Crew
from pydantic import BaseModel

class Score(BaseModel):
    score : int
    reason : str
    
@CrewBase
class SeoCrew:
    
    @agent
    def seo_expert(self):
        return Agent(
            role="SEO 전문가",
            goal="SEO 최적화를 위해 블로그 게시물을 분석하고 자세한 근거를 바탕으로 점수를 제공합니다. 매우 매우 매우 엄격하게 평가해야 하며, 제대로 평가받지 못한 게시물에는 높은 점수를 주지 마십시오.",
            backstory="""귀하는 콘텐츠 최적화에 대한 전문 지식을 갖춘 숙련된 SEO 전문가입니다.
            키워드 사용, 메타 설명, 콘텐츠 구조, 가독성, 검색 의도 정렬 등을 고려하여 블로그 게시물을 분석하여
            검색 엔진에서 콘텐츠 순위를 높이는 데 기여합니다.""",
            verbose=True,   
        )
    
    @task
    def seo_audit(self):
        return Task(
            description="""블로그 게시물의 SEO 효과를 분석하고 다음을 제공합니다.

            1. 다음을 기준으로 0~10점의 SEO 점수를 매깁니다.
            - 키워드 최적화
            - 제목 효과
            - 콘텐츠 구조(헤더, 단락)
            - 콘텐츠 길이 및 품질
            - 가독성
            - 검색 의도 정렬

            2. 다음 사항에 중점을 두고 점수를 설명하는 명확한 이유
            - 주요 강점(점수가 높은 경우)
            - 개선이 필요한 주요 약점(점수가 낮은 경우)
            - 점수에 영향을 미치는 가장 중요한 요소

            분석할 블로그 게시물: {blog_post}
            대상 주제: {topic}
            """,
            expected_output="""Score 객체:
            - 점수: SEO 품질을 평가하는 0~10 사이의 정수
            - 이유: 점수에 영향을 미치는 주요 요소를 설명하는 문자열""",
            agent=self.seo_expert(),
            output_pydantic = Score,
        )
        
    @crew
    def crew(self):
        return Crew(
            agents=self.agents,
            tasks = self.tasks,
            verbose = True,
        )
        