# 구현 계획 (Implementation Plan)

## TDD 방식 단계별 구현

### Phase 0: 프로젝트 초기 설정

#### Task 0.1: 디렉토리 구조 생성
- [ ] `src/zetasql_demo/` 패키지 생성
- [ ] 하위 패키지 생성: `catalog/`, `options/`, `lineage/`, `examples/`
- [ ] 각 패키지에 `__init__.py` 생성
- [ ] `tests/` 디렉토리 생성
- [ ] `pytest.ini` 설정 파일 생성

#### Task 0.2: 공통 테스트 설정
- [ ] `tests/conftest.py` 생성
- [ ] `@pytest.fixture` 정의:
  - `sample_catalog`: 재사용 가능한 샘플 카탈로그
  - `language_options`: BigQuery LanguageOptions
  - `analyzer`: 설정된 Analyzer 인스턴스

#### Task 0.3: 데이터 모델 정의
- [ ] `src/zetasql_demo/lineage/models.py` 생성
- [ ] `@dataclass` 정의:
  - `TableEntity`
  - `ColumnEntity`
  - `TableLineage`
  - `ColumnLineage`

**완료 조건**: 디렉토리 구조 생성 완료, 빈 `__init__.py` 파일들 존재

---

### Phase 1: 카탈로그 & 옵션 모듈 (TDD)

#### Task 1.1: 카탈로그 테스트 작성 (RED)
**파일**: `tests/test_catalog.py`

테스트 케이스:
- [ ] `test_create_sample_catalog()`: 카탈로그 생성 및 구조 확인
- [ ] `test_catalog_has_orders_table()`: orders 테이블 존재 확인
- [ ] `test_catalog_has_customers_table()`: customers 테이블 존재 확인
- [ ] `test_catalog_has_products_table()`: products 테이블 존재 확인
- [ ] `test_orders_table_columns()`: orders 테이블의 컬럼 확인
- [ ] `test_customers_table_columns()`: customers 테이블의 컬럼 확인
- [ ] `test_products_table_columns()`: products 테이블의 컬럼 확인
- [ ] `test_catalog_has_builtin_functions()`: builtin functions 포함 확인

**실행**: `pytest tests/test_catalog.py -v` → 모두 실패해야 함

#### Task 1.2: 카탈로그 구현 (GREEN)
**파일**: `src/zetasql_demo/catalog/sample_catalog.py`

구현:
- [ ] `create_sample_catalog()` 함수
  - orders 테이블: order_id, customer_id, product_id, quantity, amount, order_date
  - customers 테이블: customer_id, name, email, country
  - products 테이블: product_id, name, price, category
  - BigQuery 스타일 네이밍: `myproject.sales.orders` 등
  - Builtin functions 포함

**실행**: `pytest tests/test_catalog.py -v` → 모두 통과해야 함

#### Task 1.3: BigQuery 옵션 테스트 작성 (RED)
**파일**: `tests/test_bigquery_options.py`

테스트 케이스:
- [ ] `test_get_bigquery_language_options()`: 함수 실행 확인
- [ ] `test_has_qualify_feature()`: QUALIFY 기능 활성화 확인
- [ ] `test_has_pivot_feature()`: PIVOT 기능 활성화 확인
- [ ] `test_has_unpivot_feature()`: UNPIVOT 기능 활성화 확인
- [ ] `test_has_json_features()`: JSON 관련 기능 확인
- [ ] `test_has_geography_feature()`: GEOGRAPHY 기능 확인
- [ ] `test_supported_statement_kinds()`: 지원되는 statement kinds 확인

**실행**: `pytest tests/test_bigquery_options.py -v` → 모두 실패해야 함

#### Task 1.4: BigQuery 옵션 구현 (GREEN)
**파일**: `src/zetasql_demo/options/bigquery_options.py`

구현:
- [ ] `get_bigquery_language_options()` 함수
  - LanguageOptions 생성
  - 80+ 언어 기능 활성화 (Java의 BigQueryLanguageOptions.java 참고)
  - 주요 기능: QUALIFY, PIVOT, UNPIVOT, JSON, GEOGRAPHY, NUMERIC, etc.
  - Statement kinds 설정

**실행**: `pytest tests/test_bigquery_options.py -v` → 모두 통과해야 함

**Phase 1 완료 확인**: `pytest tests/test_catalog.py tests/test_bigquery_options.py -v` → 모두 통과

---

### Phase 2: 테이블 리니지 추출 (TDD)

#### Task 2.1: 테이블 리니지 테스트 작성 (RED)
**파일**: `tests/test_table_lineage.py`

테스트 케이스:

**기본 SQL 문법**:
- [ ] `test_select_from_single_table()`: 단일 테이블 SELECT
- [ ] `test_select_with_join()`: JOIN이 포함된 SELECT
- [ ] `test_create_table_as_select()`: CREATE TABLE AS SELECT
- [ ] `test_create_view_as_select()`: CREATE VIEW AS SELECT
- [ ] `test_insert_into_table()`: INSERT INTO ... SELECT
- [ ] `test_update_table()`: UPDATE 문
- [ ] `test_merge_statement()`: MERGE 문

**복잡한 쿼리**:
- [ ] `test_select_with_subquery()`: 서브쿼리
- [ ] `test_select_with_cte()`: CTE (WITH 절)
- [ ] `test_nested_cte()`: 중첩된 CTE
- [ ] `test_multiple_joins()`: 다중 JOIN
- [ ] `test_union_query()`: UNION

**예상 결과**:
- 각 테스트는 `TableLineage` 객체 반환
- `source_tables` 집합에 올바른 테이블들 포함
- `target_table` 올바르게 설정 (또는 None)
- `statement_type` 올바르게 설정

**실행**: `pytest tests/test_table_lineage.py -v` → 모두 실패해야 함

#### Task 2.2: 테이블 리니지 추출기 구현 (GREEN)
**파일**: `src/zetasql_demo/lineage/table_lineage.py`

구현:
- [ ] `TableLineageExtractor` 클래스 (ResolvedNodeVisitor 상속)
  - `__init__()`: 초기화
  - `visit_ResolvedTableScan()`: 소스 테이블 수집
  - `visit_ResolvedCreateTableAsSelectStmt()`: CREATE TABLE AS SELECT 처리
  - `visit_ResolvedCreateViewStmt()`: CREATE VIEW 처리
  - `visit_ResolvedInsertStmt()`: INSERT 처리
  - `visit_ResolvedUpdateStmt()`: UPDATE 처리
  - `visit_ResolvedMergeStmt()`: MERGE 처리
  - `default_visit()`: 기본 동작 (descend)
  
- [ ] `extract_table_lineage()` 함수
  - ResolvedStatement 입력
  - TableLineageExtractor 실행
  - TableLineage 반환

**점진적 구현**:
1. 먼저 SELECT 문만 통과하도록 구현
2. CREATE TABLE AS SELECT 추가
3. INSERT 추가
4. UPDATE, MERGE 추가
5. 복잡한 쿼리 (서브쿼리, CTE) 처리

**실행**: 
- 구현 후 `pytest tests/test_table_lineage.py::test_select_from_single_table -v`
- 각 테스트를 하나씩 통과시킴
- 최종: `pytest tests/test_table_lineage.py -v` → 모두 통과

**Phase 2 완료 확인**: `pytest tests/test_table_lineage.py -v` → 모두 통과

---

### Phase 3: 컬럼 리니지 추출 (TDD)

#### Task 3.1: 컬럼 리니지 테스트 작성 (RED)
**파일**: `tests/test_column_lineage.py`

테스트 케이스:

**기본 SQL 문법**:
- [ ] `test_select_simple_columns()`: 단순 컬럼 선택 (SELECT a, b FROM table)
- [ ] `test_select_with_expression()`: 표현식 (SELECT a + b FROM table)
- [ ] `test_select_with_function()`: 함수 (SELECT UPPER(name) FROM table)
- [ ] `test_select_with_alias()`: 별칭 (SELECT a AS x FROM table)
- [ ] `test_select_with_join()`: JOIN의 컬럼 리니지
- [ ] `test_create_table_as_select_lineage()`: CREATE TABLE AS SELECT
- [ ] `test_insert_column_lineage()`: INSERT INTO
- [ ] `test_update_column_lineage()`: UPDATE SET
- [ ] `test_merge_column_lineage()`: MERGE

**복잡한 표현식**:
- [ ] `test_case_expression()`: CASE WHEN
- [ ] `test_aggregate_function()`: SUM, AVG 등
- [ ] `test_window_function()`: ROW_NUMBER() OVER
- [ ] `test_subquery_in_select()`: 서브쿼리의 컬럼 참조
- [ ] `test_cte_column_lineage()`: CTE의 컬럼 리니지

**예상 결과**:
- 각 테스트는 `list[ColumnLineage]` 반환
- 각 `ColumnLineage`는 `target` 컬럼과 `parents` 컬럼 집합 포함
- 표현식의 경우 관련된 모든 소스 컬럼 추적

**실행**: `pytest tests/test_column_lineage.py -v` → 모두 실패해야 함

#### Task 3.2: ParentColumnFinder 구현 (GREEN)
**파일**: `src/zetasql_demo/lineage/column_lineage.py` (part 1)

구현:
- [ ] `ParentColumnFinder` 클래스 (ResolvedNodeVisitor 상속)
  - `__init__()`: column_map, parent_map, terminal_columns 초기화
  - `visit_ResolvedTableScan()`: terminal columns 등록
  - `visit_ResolvedComputedColumn()`: 계산된 컬럼의 부모 추적
  - `visit_ResolvedColumnRef()`: 컬럼 참조 기록
  - `visit_ResolvedProjectScan()`: 프로젝션 처리
  - `_extract_column_refs()`: 표현식에서 컬럼 참조 추출
  - `find_terminal_parents()`: BFS로 terminal parents 찾기

**실행**: 중간 테스트 - 일부 단순 테스트부터 통과 확인

#### Task 3.3: ColumnLineageExtractor 구현 (GREEN)
**파일**: `src/zetasql_demo/lineage/column_lineage.py` (part 2)

구현:
- [ ] `ColumnLineageExtractor` 클래스
  - `extract_for_query_stmt()`: SELECT 문 처리
  - `extract_for_create_table_as_select()`: CREATE TABLE AS SELECT 처리
  - `extract_for_insert()`: INSERT 처리
  - `extract_for_update()`: UPDATE 처리
  - `extract_for_merge()`: MERGE 처리
  
- [ ] `extract_column_lineage()` 함수
  - ResolvedStatement 입력
  - Statement 타입에 따라 적절한 extractor 메서드 호출
  - list[ColumnLineage] 반환

**점진적 구현**:
1. 단순 SELECT (컬럼 직접 참조)
2. 표현식 (산술 연산, 함수)
3. JOIN
4. CREATE TABLE AS SELECT, INSERT
5. UPDATE, MERGE
6. 복잡한 표현식 (CASE, 윈도우 함수, 서브쿼리)

**실행**:
- 각 테스트를 하나씩 통과시킴
- 최종: `pytest tests/test_column_lineage.py -v` → 모두 통과

**Phase 3 완료 확인**: `pytest tests/test_column_lineage.py -v` → 모두 통과

---

### Phase 4: 결과 포맷팅 (TDD)

#### Task 4.1: 포맷터 테스트 작성 (RED)
**파일**: `tests/test_formatters.py`

테스트 케이스:
- [ ] `test_table_lineage_to_json()`: 테이블 리니지 JSON 변환
- [ ] `test_table_lineage_to_text()`: 테이블 리니지 텍스트 변환
- [ ] `test_column_lineage_to_json()`: 컬럼 리니지 JSON 변환
- [ ] `test_column_lineage_to_text()`: 컬럼 리니지 텍스트 변환
- [ ] `test_json_is_valid()`: JSON 유효성 확인
- [ ] `test_text_is_readable()`: 텍스트 가독성 확인

**실행**: `pytest tests/test_formatters.py -v` → 모두 실패해야 함

#### Task 4.2: 포맷터 구현 (GREEN)
**파일**: `src/zetasql_demo/lineage/formatters.py`

구현:
- [ ] `LineageFormatter` 클래스
  - `table_lineage_to_json()`: 딕셔너리로 변환 후 json.dumps()
  - `table_lineage_to_text()`: 읽기 쉬운 텍스트 형식
  - `column_lineage_to_json()`: 리스트를 JSON으로 변환
  - `column_lineage_to_text()`: 각 컬럼별로 부모 컬럼 나열

**텍스트 출력 예시**:
```
Table Lineage:
  Statement: CREATE TABLE AS SELECT
  Target: myproject.analytics.order_summary
  Sources:
    - myproject.sales.orders
    - myproject.sales.customers

Column Lineage:
  myproject.analytics.order_summary.total_amount
    ← myproject.sales.orders.amount
    ← myproject.sales.orders.quantity
  myproject.analytics.order_summary.customer_name
    ← myproject.sales.customers.name
```

**실행**: `pytest tests/test_formatters.py -v` → 모두 통과

**Phase 4 완료 확인**: `pytest tests/test_formatters.py -v` → 모두 통과

---

### Phase 5: 시연 스크립트 & 문서화

#### Task 5.1: 테이블 리니지 시연 스크립트
**파일**: `src/zetasql_demo/examples/demo_table_lineage.py`

구현:
- [ ] 카탈로그 및 Analyzer 설정
- [ ] 다양한 SQL 문 예제:
  - SELECT with JOIN
  - CREATE TABLE AS SELECT
  - INSERT INTO
  - UPDATE
  - MERGE
  - CTE
- [ ] 각 예제별로:
  - SQL 문 출력
  - 테이블 리니지 추출
  - JSON 및 텍스트 형식으로 출력
  - 구분선 출력

**실행**: `python src/zetasql_demo/examples/demo_table_lineage.py`

#### Task 5.2: 컬럼 리니지 시연 스크립트
**파일**: `src/zetasql_demo/examples/demo_column_lineage.py`

구현:
- [ ] 카탈로그 및 Analyzer 설정
- [ ] 다양한 SQL 문 예제:
  - 단순 SELECT
  - 표현식 (산술, 함수)
  - JOIN
  - CREATE TABLE AS SELECT
  - INSERT
  - CASE WHEN
  - 윈도우 함수
- [ ] 각 예제별로:
  - SQL 문 출력
  - 컬럼 리니지 추출
  - JSON 및 텍스트 형식으로 출력

**실행**: `python src/zetasql_demo/examples/demo_column_lineage.py`

#### Task 5.3: README 작성
**파일**: `README.md`

내용:
- [ ] 프로젝트 개요
- [ ] 기능 설명
- [ ] 요구사항 (Python 버전, 의존성)
- [ ] 설치 방법
- [ ] 실행 방법:
  - 테스트 실행
  - 시연 스크립트 실행
- [ ] 예제 결과 스크린샷 (옵션)
- [ ] 프로젝트 구조 설명
- [ ] 참고 자료 (zetasql-toolkit 레포 링크)

---

## 체크리스트

### Phase 0: 초기 설정
- [ ] 디렉토리 구조 생성
- [ ] conftest.py 작성
- [ ] models.py 작성

### Phase 1: 카탈로그 & 옵션
- [ ] test_catalog.py 작성 (RED)
- [ ] sample_catalog.py 구현 (GREEN)
- [ ] test_bigquery_options.py 작성 (RED)
- [ ] bigquery_options.py 구현 (GREEN)
- [ ] Phase 1 전체 테스트 통과

### Phase 2: 테이블 리니지
- [ ] test_table_lineage.py 작성 (RED)
- [ ] table_lineage.py 구현 (GREEN)
- [ ] 모든 SQL 문법 지원 확인
- [ ] 복잡한 쿼리 지원 확인
- [ ] Phase 2 전체 테스트 통과

### Phase 3: 컬럼 리니지
- [ ] test_column_lineage.py 작성 (RED)
- [ ] ParentColumnFinder 구현 (GREEN)
- [ ] ColumnLineageExtractor 구현 (GREEN)
- [ ] 모든 SQL 문법 지원 확인
- [ ] 복잡한 표현식 지원 확인
- [ ] Phase 3 전체 테스트 통과

### Phase 4: 포맷팅
- [ ] test_formatters.py 작성 (RED)
- [ ] formatters.py 구현 (GREEN)
- [ ] Phase 4 전체 테스트 통과

### Phase 5: 시연 & 문서
- [ ] demo_table_lineage.py 작성
- [ ] demo_column_lineage.py 작성
- [ ] README.md 작성
- [ ] 시연 스크립트 정상 실행 확인

### 최종 확인
- [ ] `pytest tests/ -v` → 모든 테스트 통과
- [ ] `python src/zetasql_demo/examples/demo_table_lineage.py` → 정상 실행
- [ ] `python src/zetasql_demo/examples/demo_column_lineage.py` → 정상 실행
- [ ] 문서 완성도 확인

---

## 예상 소요 시간

| Phase | 예상 시간 | 설명 |
|-------|----------|------|
| Phase 0 | 30분 | 초기 설정 및 데이터 모델 |
| Phase 1 | 1시간 | 카탈로그 & 옵션 (비교적 단순) |
| Phase 2 | 2시간 | 테이블 리니지 (Visitor 패턴 적용) |
| Phase 3 | 3-4시간 | 컬럼 리니지 (복잡한 로직) |
| Phase 4 | 30분 | 포맷팅 (단순) |
| Phase 5 | 1시간 | 시연 & 문서 |
| **총계** | **8-9시간** | |

---

## 주요 마일스톤

1. **M1**: Phase 0-1 완료 → 카탈로그와 옵션 모듈 작동
2. **M2**: Phase 2 완료 → 테이블 리니지 추출 작동
3. **M3**: Phase 3 완료 → 컬럼 리니지 추출 작동
4. **M4**: Phase 4-5 완료 → 전체 시연 가능

---

## 리스크 & 대응

| 리스크 | 영향 | 대응책 |
|--------|------|--------|
| Python ZetaSQL API가 Java와 다름 | 높음 | 문서 참고, 유사한 API 찾기 |
| Visitor 패턴 복잡도 | 중간 | 단순한 케이스부터 점진적 구현 |
| 컬럼 리니지 알고리즘 복잡 | 높음 | Java 코드를 면밀히 분석, 단계별 구현 |
| 복잡한 SQL 문법 지원 | 중간 | 핵심 케이스 먼저 구현, 추가는 점진적 |

---

## 성공 기준

- [ ] 모든 테스트 통과 (100% pass)
- [ ] 모든 지원 SQL 문법 작동 (SELECT, CREATE, INSERT, UPDATE, MERGE)
- [ ] 복잡한 쿼리 처리 (서브쿼리, CTE, 윈도우 함수)
- [ ] 시연 스크립트 정상 실행
- [ ] 문서 완성
