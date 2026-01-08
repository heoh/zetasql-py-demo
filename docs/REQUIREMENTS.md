# 요구사항 명세

## 기능 요구사항

### FR-1: BigQuery LanguageOptions 지원
- Java의 `BigQueryLanguageOptions.java`와 동일한 80+ 언어 기능 활성화
- `ProductMode.PRODUCT_EXTERNAL` 설정
- `NameResolutionMode.NAME_RESOLUTION_DEFAULT` 설정
- 주요 기능:
  - JSON 타입 및 함수
  - GEOGRAPHY 타입
  - NUMERIC, BIGNUMERIC 타입
  - PIVOT, UNPIVOT
  - QUALIFY 절
  - Analytic functions (윈도우 함수)
  - Table-valued functions (TVF)
  - DML: INSERT, UPDATE, MERGE, DELETE
  - DDL: CREATE TABLE, CREATE VIEW, ALTER, DROP

### FR-2: 테스트용 카탈로그 생성
- BigQuery 스타일 3-part 네이밍: `project.dataset.table`
- `CatalogBuilder`와 `TableBuilder` 활용
- 재사용 가능한 샘플 테이블 정의
- Builtin functions 포함

**샘플 테이블:**
- `project1.dataset1.orders` (order_id, customer_id, amount, order_date)
- `project1.dataset1.customers` (customer_id, name, email, region)
- `project1.dataset1.products` (product_id, name, price, category)
- `project1.dataset1.order_items` (order_id, product_id, quantity, price)

### FR-3: 테이블 레벨 리니지 추출

#### 지원 SQL 문법
1. **SELECT**
   ```sql
   SELECT * FROM project.dataset.source_table
   ```
   - 소스: `project.dataset.source_table`
   - 타겟: 없음 (쿼리 결과만)

2. **CREATE TABLE AS SELECT**
   ```sql
   CREATE TABLE project.dataset.target AS
   SELECT col1, col2 FROM project.dataset.source
   ```
   - 소스: `project.dataset.source`
   - 타겟: `project.dataset.target`

3. **CREATE VIEW**
   ```sql
   CREATE VIEW project.dataset.view_name AS
   SELECT * FROM project.dataset.source
   ```
   - 소스: `project.dataset.source`
   - 타겟: `project.dataset.view_name`

4. **INSERT**
   ```sql
   INSERT INTO project.dataset.target
   SELECT * FROM project.dataset.source
   ```
   - 소스: `project.dataset.source`
   - 타겟: `project.dataset.target`

5. **UPDATE**
   ```sql
   UPDATE project.dataset.target t
   SET col1 = s.col1
   FROM project.dataset.source s
   WHERE t.id = s.id
   ```
   - 소스: `project.dataset.source`, `project.dataset.target`
   - 타겟: `project.dataset.target`

6. **MERGE**
   ```sql
   MERGE project.dataset.target t
   USING project.dataset.source s
   ON t.id = s.id
   WHEN MATCHED THEN UPDATE SET col1 = s.col1
   WHEN NOT MATCHED THEN INSERT (col1) VALUES (s.col1)
   ```
   - 소스: `project.dataset.source`, `project.dataset.target`
   - 타겟: `project.dataset.target`

#### 복잡한 쿼리 지원
- **서브쿼리**
  ```sql
  SELECT * FROM (SELECT * FROM table1) AS sub
  ```
- **CTE (WITH 절)**
  ```sql
  WITH cte AS (SELECT * FROM table1)
  SELECT * FROM cte
  ```
- **JOIN**
  ```sql
  SELECT * FROM table1 t1
  JOIN table2 t2 ON t1.id = t2.id
  ```
- **UNION**
  ```sql
  SELECT * FROM table1
  UNION ALL
  SELECT * FROM table2
  ```

### FR-4: 컬럼 레벨 리니지 추출

#### Java 구현 포팅
- `ColumnLineageExtractor.java` 로직
- `ParentColumnFinder.java` 로직
- `ExpressionParentFinder.java` 로직
- `ColumnEntity.java`, `ColumnLineage.java` 모델

#### 핵심 개념
- **Terminal Columns**: 테이블에서 직접 읽는 컬럼 (최종 소스)
- **Computed Columns**: 다른 컬럼으로부터 계산된 컬럼
- **Parent Tracking**: BFS로 컬럼의 최종 소스 추적

#### 지원 시나리오
1. **단순 컬럼 참조**
   ```sql
   SELECT col1 AS alias FROM table1
   ```
   - `alias` <- `table1.col1`

2. **함수 적용**
   ```sql
   SELECT UPPER(col1) AS upper_col FROM table1
   ```
   - `upper_col` <- `table1.col1`

3. **다중 컬럼 조합**
   ```sql
   SELECT CONCAT(col1, col2) AS combined FROM table1
   ```
   - `combined` <- `table1.col1`, `table1.col2`

4. **서브쿼리**
   ```sql
   SELECT outer_col FROM (
     SELECT col1 AS outer_col FROM table1
   )
   ```
   - `outer_col` <- `table1.col1`

5. **CTE**
   ```sql
   WITH cte AS (SELECT col1 AS cte_col FROM table1)
   SELECT cte_col FROM cte
   ```
   - `cte_col` <- `table1.col1`

6. **JOIN**
   ```sql
   SELECT t1.col1, t2.col2
   FROM table1 t1
   JOIN table2 t2 ON t1.id = t2.id
   ```
   - `col1` <- `table1.col1`
   - `col2` <- `table2.col2`

7. **집계 함수**
   ```sql
   SELECT SUM(amount) AS total FROM orders
   ```
   - `total` <- `orders.amount`

8. **윈도우 함수**
   ```sql
   SELECT ROW_NUMBER() OVER (PARTITION BY col1 ORDER BY col2) AS rn
   FROM table1
   ```
   - `rn` <- `table1.col1`, `table1.col2`

9. **STRUCT 확장**
   ```sql
   SELECT struct_col.field1 FROM table1
   ```
   - `field1` <- `table1.struct_col.field1`

### FR-5: 리니지 결과 포맷팅

#### 데이터 모델 (dataclass)
```python
@dataclass
class ColumnEntity:
    table: str
    name: str

@dataclass
class ColumnLineage:
    target: ColumnEntity
    parents: Set[ColumnEntity]

@dataclass
class TableLineage:
    target: Optional[str]
    sources: Set[str]
```

#### JSON 출력
```python
def to_json(lineage: List[ColumnLineage]) -> str:
    # Pretty-printed JSON with proper serialization
```

#### 텍스트 출력
```python
def to_text(lineage: List[ColumnLineage]) -> str:
    # Human-readable format with indentation
```

### FR-6: 시연 예제

#### 테이블 리니지 데모
- 다양한 SQL 문법별 리니지 추출 시연
- 출력: JSON + 텍스트 형식

#### 컬럼 리니지 데모
- Java `ExtractColumnLevelLineage.java`와 동일한 예제
- CREATE TABLE AS SELECT, INSERT, UPDATE, MERGE 시연
- 출력: JSON + 텍스트 형식

## 비기능 요구사항

### NFR-1: 코드 품질
- Type hints 사용
- Docstring 작성 (Google 스타일)
- 100% 테스트 커버리지 목표

### NFR-2: 테스트
- pytest 프레임워크
- 단위 테스트: 각 모듈별 독립적 테스트
- 통합 테스트: 전체 플로우 검증
- Fixture: 재사용 가능한 catalog, analyzer

### NFR-3: 문서화
- README: 설치 및 실행 방법
- Docstring: 모든 public 함수/클래스
- 예제 코드: 주석으로 설명

### NFR-4: 가독성
- 명확한 변수명
- 함수는 한 가지 역할만
- 복잡한 로직은 주석으로 설명
- Java 구현과 유사한 구조 유지 (포팅 용이성)

## 제외 사항

- 실제 BigQuery 연결 기능
- 에러 처리 상세 테스트 (기본 try-except만)
- 성능 최적화 (정확성 우선)
- CLI 인터페이스 (Python 스크립트 직접 실행)
