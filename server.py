import sys
import json
import argparse
import asyncio
import logging

def setup_check_mode_encoding():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

import mcp.types as types
from mcp.server.stdio import stdio_server

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("oracle-sync-server")

SYNC_INPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "source_user": {"type": "string", "description": "소스 DB 유저"},
        "source_password": {"type": "string", "description": "소스 DB 비밀번호"},
        "source_dsn": {"type": "string", "description": "소스 DB DSN (예: host:port/service)"},
        "target_user": {"type": "string", "description": "타겟 DB 유저"},
        "target_password": {"type": "string", "description": "타겟 DB 비밀번호"},
        "target_dsn": {"type": "string", "description": "타겟 DB DSN"},
        "table_name": {"type": "string", "description": "동기화할 테이블명"},
        "where_condition": {"type": "string", "description": "데이터 추출 WHERE 조건 (예: ID > 100)"}
    },
    "required": [
        "source_user", "source_password", "source_dsn",
        "target_user", "target_password", "target_dsn",
        "table_name", "where_condition"
    ]
}

# 구버전/신버전 스키마 속성명 호환성 처리
try:
    SYNC_TOOL = types.Tool(
        name="db.sync_table",
        description="소스 오라클 DB에서 지정된 조건의 데이터를 추출하여 타겟 DB로 동기화합니다.",
        input_schema=SYNC_INPUT_SCHEMA
    )
except TypeError:
    SYNC_TOOL = types.Tool(
        name="db.sync_table",
        description="소스 오라클 DB에서 지정된 조건의 데이터를 추출하여 타겟 DB로 동기화합니다.",
        inputSchema=SYNC_INPUT_SCHEMA
    )

def perform_sync(args: dict) -> str:
    import oracledb
    log = []
    table_name = args['table_name']
    log.append("1. 소스 DB 연결 시도...")
    try:
        with oracledb.connect(user=args['source_user'], password=args['source_password'], dsn=args['source_dsn']) as src_conn:
            log.append("  -> 소스 DB 연결 성공.")
            with src_conn.cursor() as src_cur:
                log.append(f"2. 소스 테이블({table_name}) 구조 분석 중...")
                src_cur.execute(
                    "SELECT COLUMN_NAME, DATA_TYPE, DATA_LENGTH FROM ALL_TAB_COLUMNS WHERE TABLE_NAME = UPPER(:1) ORDER BY COLUMN_ID",
                    [table_name]
                )
                cols = src_cur.fetchall()
                if not cols:
                    raise ValueError(f"소스 DB에 테이블({table_name})이 존재하지 않거나 권한이 없습니다.")
                log.append(f"  -> {len(cols)}개 컬럼 정보 확인 완료.")

                log.append(f"3. 데이터 추출 중 (조건: {args['where_condition']})...")
                query = f"SELECT * FROM {table_name} WHERE {args['where_condition']}"
                src_cur.execute(query)
                rows = src_cur.fetchall()
                col_names = [desc[0] for desc in src_cur.description]
                log.append(f"  -> {len(rows)}건 데이터 추출 완료.")

        log.append("4. 타겟 DB 연결 시도...")
        with oracledb.connect(user=args['target_user'], password=args['target_password'], dsn=args['target_dsn']) as tgt_conn:
            log.append("  -> 타겟 DB 연결 성공.")
            with tgt_conn.cursor() as tgt_cur:
                tgt_cur.execute("SELECT COUNT(*) FROM ALL_TABLES WHERE TABLE_NAME = UPPER(:1)", [table_name])
                table_exists = tgt_cur.fetchone()[0] > 0

                if not table_exists:
                    log.append(f"5. 타겟 테이블이 없어 생성을 시도합니다...")
                    col_defs = []
                    for cname, ctype, clen in cols:
                        if ctype in ('VARCHAR2', 'CHAR'):
                            col_defs.append(f"{cname} {ctype}({clen})")
                        else:
                            col_defs.append(f"{cname} {ctype}")
                    ddl = f"CREATE TABLE {table_name} ({', '.join(col_defs)})"
                    tgt_cur.execute(ddl)
                    log.append("  -> 타겟 테이블 생성 완료.")
                else:
                    log.append("5. 타겟 테이블이 이미 존재하여 생성을 건너뜁니다.")

                if rows:
                    log.append("6. 타겟 테이블에 추출 데이터 입력 중...")
                    binds = [f":{i+1}" for i in range(len(col_names))]
                    insert_sql = f"INSERT INTO {table_name} ({', '.join(col_names)}) VALUES ({', '.join(binds)})"
                    tgt_cur.executemany(insert_sql, rows)
                    tgt_conn.commit()
                    log.append(f"  -> {len(rows)}건 데이터 입력 및 커밋 완료.")
                else:
                    log.append("6. 입력할 대상 데이터가 없습니다.")

        log.append("7. 데이터 동기화 전체 프로세스가 완료되었습니다.")
        return "\n".join(log)

    except Exception as e:
        log.append(f"[오류 발생] 프로세스 중단: {str(e)}")
        return "\n".join(log)

async def run_server():
    """서버 런타임 모드일 때만 서버 객체를 생성하도록 분리 (점검 모드 에러 원천 차단)"""
    from mcp.server import Server
    app = Server("oracle-sync-server")

    # 여기서부터 서버 모드에서만 실행되므로 점검 모드(--check)에서는 에러가 발생하지 않습니다.
    if hasattr(app, "list_tools"):
        @app.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            return [SYNC_TOOL]

        @app.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            if name != "db.sync_table":
                raise ValueError(f"Unknown Tool: {name}")
            result_log = await asyncio.to_thread(perform_sync, arguments)
            return [types.TextContent(type="text", text=result_log)]
    else:
        # 매우 구버전인 경우의 폴백
        async def on_list_tools(request) -> types.ListToolsResult:
            return types.ListToolsResult(tools=[SYNC_TOOL])
        app.request_handlers = {types.ListToolsRequest: on_list_tools}

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

def run_check_mode(args):
    setup_check_mode_encoding()
    
    if args.list_tools:
        print(json.dumps([{"name": SYNC_TOOL.name, "schema": SYNC_INPUT_SCHEMA}], indent=2, ensure_ascii=False))
        sys.exit(0)
        
    elif args.call:
        if args.call != "db.sync_table":
            print(f"Tool '{args.call}'을(를) 찾을 수 없습니다.")
            sys.exit(1)
        if not args.yes:
            print("db.sync_table은 WRITE 부작용이 있는 Tool입니다. 실행하려면 --yes 플래그를 추가하십시오.")
            sys.exit(1)
            
        try:
            call_args = json.loads(args.args) if args.args else {}
            print("Tool 실행 중...")
            result = perform_sync(call_args)
            print("=== 실행 결과 ===")
            print(result)
            sys.exit(0)
        except Exception as e:
            print(f"실행 실패: {e}")
            sys.exit(1)
            
    elif args.check:
        try:
            with open(args.manifest, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception as e:
            print(f"매니페스트 읽기 실패: {e}")
            sys.exit(1)
            
        errors = []
        if manifest.get("transport", {}).get("entrypoint") != "server.py":
            errors.append("transport.entrypoint가 'server.py'와 다릅니다.")
            
        declared_tools = manifest.get("declared_tools", [])
        if len(declared_tools) != 1 or declared_tools[0].get("tool_name") != SYNC_TOOL.name:
            errors.append("tools_snapshot_mismatch: 선언된 Tool 이름이 실제와 다릅니다.")
            
        if declared_tools and declared_tools[0].get("input_schema") != SYNC_INPUT_SCHEMA:
            errors.append("tools_snapshot_mismatch: 선언된 input_schema가 실제와 다릅니다.")
            
        permissions = declared_tools[0].get("permissions", {}) if declared_tools else {}
        if not permissions.get("allowed_roles") or not permissions.get("allowed_orgs"):
            errors.append("permissions.allowed_roles 또는 allowed_orgs가 비어 있습니다.")
            
        if declared_tools and declared_tools[0].get("risk_level") == "WRITE":
            if declared_tools[0].get("confirmation_policy") == "NEVER":
                errors.append("WRITE Tool은 confirmation_policy를 NEVER로 설정할 수 없습니다.")
                
        if errors:
            print("점검 실패! 다음 문제를 수정하십시오:")
            for err in errors:
                print(f" - {err}")
            sys.exit(1)
        else:
            print("매니페스트와 서버 코드가 완벽하게 일치하며 모든 제약사항을 통과했습니다. (OK)")
            sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="오라클 DB 동기화 MCP 서버")
    parser.add_argument("--check", action="store_true", help="매니페스트 및 서버 정합성 검사")
    parser.add_argument("--list-tools", action="store_true", help="지원하는 Tool 목록 출력")
    parser.add_argument("--call", type=str, help="호출할 Tool 이름")
    parser.add_argument("--args", type=str, help="Tool에 전달할 JSON 문자열 인자")
    parser.add_argument("--yes", action="store_true", help="WRITE Tool 터미널 호출 확인 플래그")
    parser.add_argument("--manifest", type=str, default="mcp-server-manifest.json", help="매니페스트 파일 경로")
    
    args = parser.parse_args()
    
    if any([args.check, args.list_tools, args.call is not None, args.help if hasattr(args, 'help') else False]):
        run_check_mode(args)
    else:
        asyncio.run(run_server())