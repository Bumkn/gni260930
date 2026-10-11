당신은 사내 폐쇄망 플랫폼 ai-hub에 등록할 MCP(Model Context Protocol) 서버를 작성한다.
아래 「아이디어」를 「제약사항」에 맞춰 개발해 주세요.

아이디어
목적
소스 db에 접속하여 주어진 테이블명, where 조건으로 data를 추출하여 타켓 db에 접속하여 같은 테이블명이 없으면 생성하고, 추출된 data를 입력한다.
흐름
소스 db, 타겟 db, 소스 테이블명, where 조건이 주어지면 실행된다.
단계 단계마다 진행여부 확인한다.
제공할 기능
소스 db에 접속해서 테이블 분석
연결 대상과 데이터
오라클 11g 이상
기타
위 아이디어를 아래 제약사항을 지켜 개발해 주세요.

제약사항은 등록 API와 실행 런타임이 실제로 검사하는 것이다. 하나라도 어기면 등록이 거부되거나, 등록은 되고 실행만 조용히 실패한다. 아이디어와 제약사항이 충돌하면 제약사항이 우선이고, 무엇을 어떻게 바꿨는지 마지막에 한 줄로 알려 준다.
아이디어에 빠진 것이 있으면 임의로 정하지 말고 무엇이 필요한지 먼저 묻는다. 다만 소유 조직이나 작성자처럼 사소한 값은 자리표시자(<조직>)로 두고 진행해도 된다.
제약사항
산출물
파일 두 개만 만든다.

server.py (또는 server.js) — MCP 서버 구현 + 터미널 점검 모드(아래 참고)
mcp-server-manifest.json — 등록용 매니페스트
README나 설정 파일은 요청받지 않았다면 만들지 않는다. 점검 모드는 별도 파일이 아니라 진입점 파일 안에 둔다 — 파일이 늘면 업로드 목록과 검토 대상이 같이 늘어난다.

절대 하면 안 되는 것
금지 이유 어길 때
런타임에 패키지 설치 (pip install, npm install, npx, uvx) 폐쇄망이라 불가능하고, 실행 시점 코드 반입은 금지다 실행 실패
환경변수 읽기 (os.environ, process.env) 서버 프로세스는 env={} 로 뜬다. 부모 환경을 물려받지 않는다 등록은 통과, 실행만 실패
PATH에서 인터프리터 찾기 (python, python3, node) 인터프리터 절대경로는 배포 설정에서 온다 interpreter_not_configured
셸 실행 (shell=True, os.system, subprocess 로 셸 문자열) argv 배열만 쓴다. 셸 인용 규칙이 개입할 여지를 만들지 않는다 검토 반려
압축 파일로 제출 (.zip, .tar, .gz 등) 중첩 압축은 검토자가 봐야 할 것을 가린다 업로드 거부
.pyc, .sh, .bat, .ps1, .exe, .dll 포함 검토자가 읽을 수 없거나 진입점이 될 수 없다 업로드 거부
하드코딩된 비밀값·토큰·내부주소·개인정보 코드와 매니페스트 모두 검토 대상이다 검토 반려
매니페스트에 스키마에 없는 필드 추가 모든 객체가 additionalProperties: false 다 VALIDATION_ERROR
코드 제약 (STDIO 서버)
사용 가능한 것: 표준 라이브러리 + mcp SDK. 그 외 의존성이 꼭 필요하면 번들 안에 함께 넣어야 하고(vendoring), 매니페스트 transport.vendored_dependencies는 반드시 true다.
파일 개수 최대 20개, 파일당 최대 50MB, 전체 최대 150MB.
코드 파일 확장자는 .py / .js / .cjs / .mjs 만 허용된다.
진입점 파일은 반드시 업로드 목록에 포함되어야 한다. 매니페스트 transport.entrypoint와 실제 파일명이 다르면 거부된다.
진입점 경로는 번들 루트 기준 상대경로다. 절대경로, .., 역슬래시, 드라이브 문자를 쓸 수 없다.
표준출력(stdout)은 JSON-RPC 채널이다. print() 로 아무것도 찍지 않는다. 로그가 필요하면 stderr로 보낸다.
터미널 점검 인터페이스 (필수)
ai-hub 화면에서만 확인할 수 있는 서버는 만들지 않는다. 등록하기 전에, 그리고 문제가 생겼을 때 터미널에서 바로 확인할 수 있어야 한다. 진입점 파일에 인자로 동작하는 점검 모드를 함께 구현한다.

최소 네 가지:
명령 하는 일 종료 코드
<진입점> --check 매니페스트와 실제 tools/list가 일치하는지, 각 Tool 의 input_schema 가 올바른 JSON Schema 인지 검사하고 결과를 사람이 읽을 수 있게 출력 문제 없으면 0, 있으면 1
<진입점> --list-tools Tool 이름·설명·입력 스키마를 표 또는 JSON 으로 출력 0
<진입점> --call <tool_name> --args '<JSON>' Tool 하나를 실제로 한 번 호출하고 결과를 출력 성공 0, 실패 1
<진입점> --help 위 사용법 0
지켜야 할 것:

인자가 없을 때만 stdio 서버로 뜬다. 점검 모드에서는 JSON-RPC 세션을 열지 않는다. 이 구분이 없으면 stdout 에 섞인 점검 출력이 프로토콜을 깨뜨린다.
매니페스트 경로는 기본값을 진입점과 같은 폴더의 mcp-server-manifest.json 으로 하고, --manifest <경로> 로 바꿀 수 있게 한다.

transport.args 에는 점검용 플래그를 절대 넣지 않는다. 거기 들어간 인자는 런타임이 서버를 띄울 때 그대로 전달되므로, 서버가 뜨지 않고 점검만 하고 끝난다.
표준 라이브러리만 쓴다(argparse, json). 점검 기능 때문에 의존성을 늘리지 않는다.

--call 은 매니페스트에 risk_level: READ_ONLY 로 선언된 Tool만 인자 없이 호출할 수 있게 한다. WRITE Tool 은 --yes 를 추가로 요구한다 — 터미널에서도 부작용은 확인을 거친다.

출력에 비밀값·내부 주소·개인정보를 넣지 않는다. 오류는 무엇을 고쳐야 하는지까지 말한다.
점검 모드 시작에서 출력 인코딩을 UTF-8 로 고정한다. 배포 대상이 사내 Windows PC 라 콘솔·파이프 기본 인코딩이 cp949 이고, 한국어를 그냥 print 하면 UnicodeEncodeError 로 점검이 죽는다(예제에서 실제로 겪었다). 서버 모드는 건드리지 않는다 — 거기 stdout 은 SDK 것이다.

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
--check 가 반드시 잡아야 하는 것(등록·실행에서 실제로 막히는 항목이다):

tools/list 의 Tool 이름 집합이 매니페스트 declared_tools 와 다름 → tools_snapshot_mismatch
input_schema 가 서로 다름 (같은 이름인데 스키마가 갈라진 경우)
transport.entrypoint 가 실제 파일명과 다름
permissions.allowed_roles 또는 allowed_orgs 가 비어 있음 (Default Deny 라 아무도 못 씀)
risk_level: WRITE 인데 confirmation_policy: NEVER
매니페스트 규격
최상위 필수 필드 11개. 순서는 아래대로 쓴다.

{
  "schema_version": "1.0",
  "id": "<새 UUID v4>",
  "type": "mcp_server",
  "name": "<128자 이내, 업무 목적이 드러나는 한국어 이름>",
  "version": "1.0.0",
  "owner": { "org": "<조직>", "team": "<팀>", "creator_id": "<이메일>" },
  "classification": "PUBLIC_INTERNAL",
  "description": "<1024자 이내. 이 서버가 무엇을 하는지, 무엇을 건드리지 않는지>",
  "tags": ["<선택>"],
  "server_alias": "<소문자-케밥-케이스>",
  "provenance": "INTERNAL",
  "protocol_version": "2025-06-18",
  "transport": {
    "kind": "STDIO",
    "interpreter": "python",
    "entrypoint": "server.py",
    "args": [],
    "vendored_dependencies": true
  },
  "declared_tools": [ ... ]
}

값 규칙:
필드 규칙
schema_version "1.0" 고정
type "mcp_server" 고정
version Semver ^\d+\.\d+\.\d+$ (선행 0 불가)
classification PUBLIC_INTERNAL | INTERNAL | CONFIDENTIAL | RESTRICTED
server_alias ^[a-z][a-z0-9-]{0,62}[a-z0-9]$ — 소문자·숫자·하이픈. 로그 키와 화면 라벨로 그대로 쓰이므로 이스케이프가 필요 없어야 한다
provenance INTERNAL(사내 제작) | THIRD_PARTY(외부 입수)
protocol_version YYYY-MM-DD. initialize 핸드셰이크가 돌려준 값을 그대로
transport.interpreter node | python 만
transport.args 최대 32개, 각 512자. 셸 문자열이 아니라 argv 배열

Tool 정의 규격
declared_tools는 1~256개. 각 항목의 필수 필드는 tool_name, risk_level, permissions다.
{
  "tool_name": "namespace.action",
  "label": "<확인 창에 뜰 짧은 설명, 200자 이내>",
  "input_schema": { "type": "object", "additionalProperties": false, "properties": {} },
  "risk_level": "READ_ONLY",
  "permissions": {
    "allowed_roles": ["USER", "CREATOR", "ADMIN"],
    "allowed_orgs": ["<조직>"]
  },
  "data_classification": "PUBLIC_INTERNAL",
  "confirmation_policy": "NEVER",
  "execution_guards": {
    "timeout_seconds": 10,
    "max_bytes": 4096,
    "rate_limit_per_minute": 30
  }
}

규칙:
tool_name — ^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*){0,4}$, 128자 이내. 점으로 네임스페이스를 나눌 수 있다(최대 5단). 경로 구분자·선행 숫자 불가.
risk_level — READ_ONLY(부작용 없음) | WRITE(부작용 있음). 특별한 이유가 없으면 READ_ONLY로 만든다. WRITE Tool은 모델이 자동으로 고를 수 없고 항상 사용자 확인을 거친다.
permissions — Default Deny다. 빈 배열은 "제한 없음"이 아니라 "아무도 못 씀"이다. allowed_roles와 allowed_orgs 둘 다 반드시 채운다. 역할 값은 USER / CREATOR / ADMIN. 최종 권한은 검토자가 조정하므로, 여기 쓰는 값은 요청이지 확정이 아니다.
confirmation_policy — NEVER | ON_PARAMETER | ALWAYS (기본 ALWAYS). risk_level: WRITE인 Tool은 NEVER를 쓸 수 없다(스키마가 거부한다).
execution_guards.timeout_seconds — 1~60. 나머지 한도는 1 이상.
input_schema — tools/list가 돌려주는 것과 같아야 한다. 입력 검증에 실패하는 Tool은 호출되지 않는다.
코드와 매니페스트의 일치
declared_tools는 서버의 tools/list 응답을 승인 시점에 찍어 둔 스냅샷이다. Tool 이름과 input_schema가 실제 응답과 다르면 연결 시점에 tools_snapshot_mismatch로 막힌다.
tools/list가 돌려주는 Tool의 개수·이름·입력 스키마를 매니페스트와 정확히 맞춘다.
실행 중에 Tool 목록을 바꾸지 않는다.
읽기 전용 Tool에는 read_only_hint=True 어노테이션을 붙인다.
출력 형식
다음 순서로만 출력한다. 설명은 각 파일 앞에 한두 문장이면 충분하다.

server.py 전체 코드 (파일 하나로 끝나게)
mcp-server-manifest.json 전체
자체 점검표 — 아래 항목에 각각 OK 또는 무엇이 문제인지 한 줄:
환경변수를 읽지 않는다
stdout에 JSON-RPC 외의 출력이 없다
런타임 패키지 설치가 없다
표준 라이브러리 + mcp 외 의존성이 없다 (있다면 무엇인지)
transport.entrypoint가 실제 파일명과 같다
declared_tools의 이름·입력 스키마가 tools/list와 일치한다
모든 Tool에 permissions.allowed_roles와 allowed_orgs가 비어 있지 않다
WRITE Tool에 confirmation_policy: NEVER가 없다
비밀값·내부주소·개인정보가 없다
인자 없이 실행하면 stdio 서버로 뜨고, 점검 플래그를 주면 서버를 띄우지 않는다
--check / --list-tools / --call / --help 가 모두 동작하고 종료 코드가 규격대로다
transport.args 에 점검용 플래그가 들어 있지 않다
아이디어에서 바꾼 것 — 제약사항 때문에 아이디어와 다르게 만든 부분이 있으면 한 줄씩. 없으면 "없음".
참고할 최소 예제
저장소의 samples/mcp-servers/hello-mcp/ 가 이 규격을 통과하는 가장 작은 예제다. 서버 구조, 매니페스트, 터미널 점검 모드까지 그대로 들어 있으니 애매하면 그것을 따른다.


uv run python samples/mcp-servers/hello-mcp/server.py --check 
