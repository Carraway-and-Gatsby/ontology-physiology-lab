# 온톨로지 그래프 탐색기

`site/index.html`을 파일 탐색기에서 브라우저로 열면 오프라인으로 사용할 수 있다. 검색, 관계 필터, 보기 전환, 노드/간선 선택, 확대/축소(버튼, Ctrl/⌘+스크롤), 초기화와 JSON 내보내기를 지원한다. 선택한 노드의 직접 이웃이 강조된다. 작은 화면에서는 노드 목록과 가로 스크롤로 접근할 수 있다.

재생성 (표준 라이브러리만 필요):

```sh
python build_graph.py --input-dir inputs --output-dir site
```

입력은 `inputs/anatomy_nodes_v2.json`, `inputs/applied_sidecar.json`, `inputs/m1_manifest.json`, 영수증은 `input-sha256.json`이다. 프로젝트 원본 리비전은 `680bd29650d97957256dd05fd3281ee8403f6aed`; 각 검사 항목에서 원본 레코드 및 JSON 위치를 확인할 수 있다. 이는 기존 기록의 읽기 전용 투영이며 새로운 매핑 검증이 아니다.

입력 생성: `anatomy_nodes_v2.json`은 `src/physiosim/ontology/anatomy_nodes_v2.json`의 복사본, `applied_sidecar.json`은 `build_applied_sidecar()` 결과(applied 데모의 `applied_sidecar.json`과 같은 직렬화), `m1_manifest.json`은 `scripts/run_four_chamber_m1.py` 출력의 `manifest.json`이다. [redacted: host] 초안은 `6f684b8` 기준 입력을 썼고, PR #4가 `anatomy_nodes_v2.json`의 `status` 문장을 고친 뒤 위 리비전에서 세 파일을 다시 생성했다(바뀐 것은 그 문장과 그에 따른 해시뿐이다). `m1_manifest.json`의 `run` 부분은 실행 환경의 의존성 버전과 출력 해시를 담으므로 실행한 컴퓨터마다 다르며, 그래프가 쓰는 `semantic_contract`는 같은 리비전에서 결정적으로 생성된다.

배치와 스타일: 지식 그래프 예시 그림처럼 흰 배경에 같은 크기(반지름 60px)의 원 노드를 유기적으로 펼친다. 노드 안에 이름을 흰색 굵은 글씨로 최대 3줄까지 쓰고 더 길면 말줄임표로 줄이며, 전체 이름은 툴팁과 검사 패널에 있다. 원본 노드는 기록된 `record.base_label`(예: cavity of left ventricle)을 본문으로, `record.key`(예: lv_cavity)를 그 아래 작은 글씨로 쓴다. 카탈로그는 읽을 수 있는 기존 이름을, 모델 노드는 변수 id를 쓴다. 간선은 검은 직선과 화살촉이고 화살촉은 대상 원의 경계에서 멈춘다. 배치는 고정 시드의 stress 배치(고정 반복 횟수; 연결된 노드 중심 간 거리는 간선 이름이 들어갈 만큼만 띄워 대체로 반지름의 3배 안팎이고, 겹침·교차가 없는 가장 촘촘한 배치를 고른 뒤 가로로 긴 캔버스에 맞게 회전) 뒤에 노드 겹침 제거, 간선이 무관한 노드를 지나지 않도록 하는 간격 보정, 교차 줄이기를 거친다. 같은 입력은 항상 같은 좌표를 낸다. 캔버스는 내용의 경계 상자에 여백(24px)을 더한 크기이고, 연결된 노드 묶음과 관계 없는 노드 묶음을 촘촘히 채운다. 데스크톱에서 그래프 영역 높이는 `max(620px, 100vh - 230px)`이다. 직선이 끝내 노드를 피하지 못하면 노드를 옮기고, 그래도 안 될 때만 그 간선을 부드러운 곡선 하나로 휜다(현재 입력에서는 세 보기 모두 휜 간선 0개, 교차 0개). 위치와 거리는 화면 정렬용일 뿐 새로운 관계나 순서를 뜻하지 않는다. 간선 레이블은 노드와 다른 레이블을 가리지 않는 위치에 놓고, 그런 위치가 없으면 숨겼다가 간선에 마우스를 올리거나 선택하면 보인다. 해당 보기에서 간선이 없는 노드는 그래프 아래 별도 묶음에 놓고, 카탈로그는 `node_class`별로 묶는다.

노드 색은 데이터에 있는 필드로만 정한다(범례에 규칙이 표시된다). 원본 템플릿은 기록된 `record.role`(Structure 초록, Space 남색, Wall 보라, Content 연보라, Tissue 갈색, Opening 청록; 범례에 `role = 값`으로 표시), 카탈로그는 `node_class`(modelled 초록, catalogue 남색, reference 보라, lumped part 연보라), 모델 노드는 레코드에 있는 구역(variables 남색, parameters 보라, volume_references 갈색, ports 짙은 회색, laws만 있으면 연보라, anatomy_roles만 있으면 청록)이다. 한 노드가 여러 구역을 가지면 이 순서의 첫 번째를 쓴다. 색은 표시 구분일 뿐 해부학적·수치적 의미가 아니다. 회색 사각형은 데이터에 실제 리터럴 값이 있는 노드에만 쓰는데 현재 입력에는 없어 쓰지 않는다. 상태는 색이 아닌 선 모양으로 구분한다: 원본 ACCEPT는 검은 실선, REVIEW는 이중선, 의존성은 긴 점선, 모델 역할은 일점쇄선, 포트 참조는 점선이다.

관계 이름: 원본 주장의 predicate IRI는 OBO Relations Ontology의 공식 rdfs:label을 표시 이름으로 쓴다(EBI OLS4 `api/ontologies/ro/properties`, 2026-11-02 확인): `BFO_0000050` part of, `RO_0001025` located in, `RO_0002572` luminal space of. 이 표는 `viewer.html`의 표시 계층에만 있고 `graph-data.json`은 기록된 IRI를 그대로 둔다. CURIE와 전체 IRI는 툴팁과 검사 패널에 나온다. 표시 이름일 뿐 새로운 해석이나 매핑 승인이 아니다. IRI가 아닌 predicate(`dependency`, `PROPOSED_BEARER_CONTEXT` 등)는 기록된 문구를 그대로 쓴다.

검사: `tests/test_graph.py`는 데이터 투영, `tests/test_layout.py`는 node로 배치를 실행해 간선이 다른 노드를 지나지 않음(간격 검사를 끄면 실패하는 회귀 포함), 노드·레이블 겹침 없음, 간선이 출발 원의 경계에서 대상 원의 경계로 이어짐, 원본 주장 보기의 교차 0개와 결정성을 확인한다. `tests/test_layout.py`에는 `node`가 필요하다.

실선 화살표는 원본 sourceTemplate → targetTemplate 주장과 원본 predicate다. 원본 ACCEPT/REVIEW는 대상 매핑 승인이 아니다. 점선은 모델 역할, 포트 참조, 의존성이며 의존성은 on → dependent이다. 해부학 관계나 수치 연결로 해석하지 않는다. 카탈로그에는 구조 간선이 없으며 31개 항목은 전체 Uberon/FMA나 OWL 추론 결과가 아니다. `role_in_smith`는 참조 모델 역할이며 M1 고유 기능의 증거가 아니다.

대상 crosswalk는 PROPOSED, 외부 수치 사용은 NONE, G3는 CLOSED다. C5는 USER_DECISION_RUNTIME_DEFERRED 및 applied false이고 기계적 bearer는 선택되지 않았다. 승모판 REVIEW/REVISE와 DRAFT 경계를 유지한다. 법칙/버전 계약 선언은 수치 무결성 증명이 아니다. 원문, 추출 사실, 해석 및 미결 충돌은 범위와 검사 패널의 원본 필드로 구분한다. 이 뷰어는 3D 형상, 시뮬레이션 또는 추론 검증을 제공하지 않는다.
