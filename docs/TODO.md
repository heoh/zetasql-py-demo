# TODO - 개발 체크리스트

## Phase 0: 프로젝트 설정 ✓
- [x] 프로젝트 구조 설계
- [x] 문서 작성 (OVERVIEW, REQUIREMENTS, ARCHITECTURE, TODO)
- [ ] README.md 작성
- [ ] pytest.ini 설정
- [ ] .gitignore 설정

## Phase 1: 카탈로그 & 옵션 (TDD)

### Step 1.1: 카탈로그 모듈
- [ ] **테스트 작성** `tests/test_catalog.py`
  - [ ] test_create_sample_catalog - 카탈로그 생성 검증
  - [ ] test_catalog_has_tables - 테이블 존재 확인
  - [ ] test_table_has_columns - 컬럼 정의 확인
  - [ ] test_builtin_functions - Builtin 함수 포함 확인
  
- [ ] **구현** `src/zetasql_demo/catalog/sample_catalog.py`
  - [ ] create_sample_catalog() 함수
  - [ ] 4개 샘플 테이블 정의 (orders, customers, products, order_items)
  - [ ] get_builtin_function_options() 함수
  
- [ ] **테스트 통과 확인** `pytest tests/test_catalog.py -v`

### Step 1.2: BigQuery 옵션 모듈
- [ ] **테스트 작성** `tests/test_bigquery_options.py`
  - [ ] test_language_features_enabled - 주요 기능 활성화 확인
    - [ ] JSON 타입/함수
    - [ ] GEOGRAPHY
    - [ ] NUMERIC/BIGNUMERIC
    - [ ] PIVOT/UNPIVOT
    - [ ] QUALIFY
    - [ ] Analytic functions
  - [ ] test_product_mode - PRODUCT_EXTERNAL 확인
  - [ ] test_name_resolution_mode - NAME_RESOLUTION_DEFAULT 확인
  - [ ] test_supported_statement_kinds - DML/DDL 지원 확인
  
- [ ] **구현** `src/zetasql_demo/options/bigquery_options.py`
  - [ ] get_bigquery_language_options() 함수
  - [ ] Java BigQueryLanguageOptions.java 80+ 기능 포팅
  - [ ] ProductMode, NameResolutionMode 설정
  
- [ ] **테스트 통과 확인** `pytest tests/test_bigquery_options.py -v`

### Step 1.3: 공통 Fixture
- [ ] **작성** `tests/conftest.py`
  - [ ] sample_catalog fixture
  - [ ] bigquery_language_options fixture
  - [ ] analyzer fixture

## Phase 2: 테이블 리니지 추출 (TDD)

### Step 2.1: 데이터 모델
- [ ] **작성** `src/zetasql_demo/lineage/models.py`
  - [ ] TableLineage dataclass
  - [ ] ColumnEntity dataclass
  - [ ] ColumnLineage dataclass

### Step 2.2: 테이블 리니지 테스트 작성 (전체)
- [ ] **테스트 작성** `tests/test_table_lineage.py`
  - [ ] test_select_single_table - 단일 테이블 SELECT
  - [ ] test_select_join - JOIN 쿼리
  - [ ] test_select_subquery - 서브쿼리
  - [ ] test_select_cte - WITH 절 (CTE)
  - [ ] test_select_union - UNION
  - [ ] test_create_table_as_select - CREATE TABLE AS SELECT
  - [ ] test_create_view - CREATE VIEW
  - [ ] test_insert - INSERT
  - [ ] test_update - UPDATE
  - [ ] test_update_with_join - UPDATE with JOIN
  - [ ] test_merge - MERGE
  - [ ] test_complex_nested_query - 복잡한 중첩 쿼리

### Step 2.3: 테이블 리니지 구현 (점진적)
- [ ] **구현** `src/zetasql_demo/lineage/table_lineage.py`
  - [ ] TableLineageExtractor 클래스 (ResolvedNodeVisitor 상속)
  - [ ] __init__ 메서드
  - [ ] visit_ResolvedTableScan - 소스 테이블 수집
  - [ ] visit_ResolvedTVFScan - TVF 처리
  - [ ] visit_ResolvedQueryStmt - SELECT 처리
  - [ ] visit_ResolvedCreateTableAsSelectStmt - CREATE TABLE AS SELECT
  - [ ] visit_ResolvedCreateViewBase - CREATE VIEW
  - [ ] visit_ResolvedInsertStmt - INSERT
  - [ ] visit_ResolvedUpdateStmt - UPDATE
  - [ ] visit_ResolvedMergeStmt - MERGE
  - [ ] extract_table_lineage() 진입점 함수
  
- [ ] **점진적 테스트 통과**
  - [ ] SELECT 관련 테스트 통과
  - [ ] CREATE 관련 테스트 통과
  - [ ] DML 관련 테스트 통과
  - [ ] 복잡한 쿼리 테스트 통과

## Phase 3: 컬럼 리니지 추출 (TDD)

### Step 3.1: 컬럼 리니지 테스트 작성 (전체)
- [ ] **테스트 작성** `tests/test_column_lineage.py`
  - [ ] test_simple_column_reference - 단순 컬럼 참조
  - [ ] test_column_alias - 컬럼 별칭
  - [ ] test_function_on_column - 함수 적용
  - [ ] test_multiple_columns_concat - 다중 컬럼 조합
  - [ ] test_subquery - 서브쿼리
  - [ ] test_cte - CTE
  - [ ] test_join - JOIN
  - [ ] test_aggregate_function - 집계 함수
  - [ ] test_window_function - 윈도우 함수
  - [ ] test_case_expression - CASE 표현식
  - [ ] test_struct_access - STRUCT 필드 접근
  - [ ] test_create_table_as_select - CREATE TABLE AS SELECT
  - [ ] test_insert - INSERT
  - [ ] test_update - UPDATE
  - [ ] test_merge - MERGE
  - [ ] test_complex_lineage - 복잡한 리니지

### Step 3.2: ExpressionParentFinder 구현
- [ ] **구현** `src/zetasql_demo/lineage/column_lineage.py`
  - [ ] ExpressionParentFinder 클래스
  - [ ] visit_ResolvedColumnRef - 컬럼 참조
  - [ ] visit_ResolvedFunctionCall - 함수 호출
  - [ ] visit_ResolvedAggregateFunctionCall - 집계 함수
  - [ ] visit_ResolvedAnalyticFunctionCall - 윈도우 함수
  - [ ] visit_ResolvedSubqueryExpr - 서브쿼리
  - [ ] visit_ResolvedGetStructField - STRUCT 필드
  - [ ] find_direct_parents() 진입점
  
- [ ] **테스트**: 표현식 관련 테스트 통과

### Step 3.3: ParentColumnFinder 구현
- [ ] **구현** `src/zetasql_demo/lineage/column_lineage.py`
  - [ ] ParentColumnFinder 클래스
  - [ ] __init__ - 맵 초기화
  - [ ] visit_ResolvedComputedColumn - Computed column 등록
  - [ ] visit_ResolvedTableScan - Terminal columns 등록
  - [ ] visit_ResolvedTVFScan - TVF terminal columns
  - [ ] visit_ResolvedWithScan - WITH 스코프 push
  - [ ] visit_ResolvedWithRefScan - WITH 참조 해결
  - [ ] visit_ResolvedSetOperationScan - UNION 등 처리
  - [ ] visit_ResolvedArrayScan - UNNEST 처리
  - [ ] expand_column() - STRUCT 확장
  - [ ] find_terminal_parents() - BFS 탐색
  - [ ] make_column_key() - 컬럼 키 생성
  
- [ ] **테스트**: 컬럼 추적 관련 테스트 통과

### Step 3.4: ColumnLineageExtractor 구현
- [ ] **구현** `src/zetasql_demo/lineage/column_lineage.py`
  - [ ] ColumnLineageExtractor 클래스
  - [ ] extract_for_output_columns() - 공통 로직
  - [ ] extract_for_create_table_as_select()
  - [ ] extract_for_create_view()
  - [ ] extract_for_query_stmt()
  - [ ] extract_for_insert()
  - [ ] extract_for_update()
  - [ ] extract_for_merge()
  - [ ] extract_column_lineage() - 진입점
  
- [ ] **테스트**: 모든 컬럼 리니지 테스트 통과

## Phase 4: 포맷터 (TDD)

### Step 4.1: 포맷터 테스트 & 구현
- [ ] **테스트 작성** `tests/test_formatters.py`
  - [ ] test_table_lineage_to_json
  - [ ] test_table_lineage_to_text
  - [ ] test_column_lineage_to_json
  - [ ] test_column_lineage_to_text
  - [ ] test_empty_lineage
  - [ ] test_multiple_parents
  
- [ ] **구현** `src/zetasql_demo/lineage/formatters.py`
  - [ ] LineageFormatter 클래스
  - [ ] to_json() - JSON 직렬화
  - [ ] to_text() - 텍스트 포맷
  - [ ] _format_table_lineage_text()
  - [ ] _format_column_lineage_text()
  
- [ ] **테스트 통과 확인**

## Phase 5: 시연 예제

### Step 5.1: 테이블 리니지 데모
- [ ] **작성** `src/zetasql_demo/examples/demo_table_lineage.py`
  - [ ] main() 함수
  - [ ] demo_select()
  - [ ] demo_create_table_as_select()
  - [ ] demo_insert()
  - [ ] demo_update()
  - [ ] demo_merge()
  - [ ] demo_complex_queries()
  - [ ] 각 예제에 주석 설명 추가
  
- [ ] **실행 확인** `python src/zetasql_demo/examples/demo_table_lineage.py`

### Step 5.2: 컬럼 리니지 데모
- [ ] **작성** `src/zetasql_demo/examples/demo_column_lineage.py`
  - [ ] main() 함수
  - [ ] demo_create_table_as_select() - Java 예제와 동일
  - [ ] demo_insert() - Java 예제와 동일
  - [ ] demo_update() - Java 예제와 동일
  - [ ] demo_merge() - Java 예제와 동일
  - [ ] output_lineage() - 결과 출력
  
- [ ] **실행 확인** `python src/zetasql_demo/examples/demo_column_lineage.py`

## Phase 6: 문서화 & 마무리

### Step 6.1: README 작성
- [ ] **작성** `README.md`
  - [ ] 프로젝트 소개
  - [ ] 설치 방법
  - [ ] 빠른 시작 (Quick Start)
  - [ ] 사용 예제
  - [ ] 테스트 실행 방법
  - [ ] 프로젝트 구조 설명
  - [ ] 참고 자료

### Step 6.2: 코드 리팩토링
- [ ] Type hints 검증
- [ ] Docstring 추가/개선
- [ ] 코드 스타일 통일
- [ ] 불필요한 코드 제거

### Step 6.3: 최종 테스트
- [ ] 전체 테스트 스위트 실행 `pytest -v`
- [ ] 커버리지 확인 `pytest --cov=src/zetasql_demo`
- [ ] 예제 스크립트 전부 실행 확인

## 진행 상황 추적

### 현재 단계
- Phase 0: 문서화 완료

### 다음 단계
- Phase 1: 카탈로그 & 옵션 구현 시작

### 완료율
- [ ] Phase 0: 80% (문서 완료, 설정 파일 남음)
- [ ] Phase 1: 0%
- [ ] Phase 2: 0%
- [ ] Phase 3: 0%
- [ ] Phase 4: 0%
- [ ] Phase 5: 0%
- [ ] Phase 6: 0%

**전체 진행률: 11%** (문서화 완료)

## 참고 사항

### Java 소스 참고 경로
- BigQuery 옵션: `.reference/zetasql-toolkit/zetasql-toolkit-bigquery/src/main/java/com/google/zetasql/toolkit/options/BigQueryLanguageOptions.java`
- 컬럼 리니지: `.reference/zetasql-toolkit/zetasql-toolkit-core/src/main/java/com/google/zetasql/toolkit/tools/lineage/`
- 예제: `.reference/zetasql-toolkit/zetasql-toolkit-examples/src/main/java/com/google/zetasql/toolkit/examples/ExtractColumnLevelLineage.java`

### 개발 시 주의사항
1. 각 Phase는 순차적으로 진행
2. 테스트 먼저 작성 (Red), 구현 (Green), 리팩토링
3. 테스트 통과 확인 후 다음 단계 진행
4. Java 구현과 비교하며 검증
5. 복잡한 쿼리는 단계적으로 지원 확대

### TDD 사이클 체크리스트
각 기능 구현 시:
- [ ] 🔴 Red: 실패하는 테스트 작성
- [ ] 🟢 Green: 최소 구현으로 테스트 통과
- [ ] 🔵 Refactor: 코드 개선
- [ ] ✅ Verify: 전체 테스트 여전히 통과하는지 확인
