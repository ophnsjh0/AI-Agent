from crewai.project import CrewBase, agent, task, crew
from crewai import Agent, Task, Crew
from pydantic import BaseModel

class Score(BaseModel):
    score : int
    reason : str
    
@CrewBase
class ViralityCrew:
    
    @agent
    def virality_expert(self):
        return Agent(
            role="소셜 미디어 바이럴 전문가",
            goal="소셜 미디어 콘텐츠의 바이럴 잠재력을 분석하고 실행 가능한 피드백을 통해 점수를 제공합니다.",
            backstory="""당신은 바이럴 콘텐츠 제작에 대한 심도 있는 전문 지식을 갖춘 소셜 미디어 전략가입니다.
            트위터와 링크드인에서 수천 개의 바이럴 게시물을 분석하여 참여, 공유, 그리고 콘텐츠 확산의 심리를 이해했습니다.
            각 플랫폼에서 바이럴을 촉진하는 구체적인 메커니즘, 즉 후크 작성부터 감정적 트리거까지 잘 알고 있습니다.""",
            verbose=True,   
        )
    
    @task
    def virality_audit(self):
        return Task(
            description="""소셜 미디어 콘텐츠의 바이럴 가능성을 분석하고 다음을 제공합니다.
            
            1. 다음을 기반으로 0~10점의 바이럴 점수 부여:
            - 후크 강도 및 관심 유도 가능성
            - 감정적 공감 및 공감도
            - 공유 가능성 요소
            - 행동 유도 효과
            - 플랫폼별 모범 사례
            - 인기 주제 정렬
            - 콘텐츠 형식 최적화
            
            2. 다음 사항에 중점을 두고 점수를 명확하게 설명하는 이유
            - 콘텐츠가 바이럴될 가능성이 높은 이유(점수가 높은 경우)
            - 바이럴성에 필요한 핵심 요소 누락(점수가 낮은 경우)
            - 가장 중요한 개선 사항
            
            분석할 콘텐츠: {content}
            콘텐츠 유형: {content_type}
            대상 주제: {topic}
            """,
            expected_output="""Score 객체:
            - score: 0~10 사이의 정수로, 바이럴 가능성을 평가합니다.
            - reason: 바이럴에 영향을 미치는 주요 요소를 설명하는 문자열입니다.""",
            agent=self.virality_expert(),
            output_pydantic = Score,
        )
        
    @crew
    def crew(self):
        return Crew(
            agents=self.agents,
            tasks = self.tasks,
            verbose = True,
        )
        