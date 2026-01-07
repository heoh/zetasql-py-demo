# 설계 문서 (Design Document)

## 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────┐
│                         사용자 (User)                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ├── python src/zetasql_demo/examples/demo_table_lineage.py
                         └── python src/zetasql_demo/examples/demo_column_lineage.py
                         │
         ┌───────────────┴───────────────┐
         │                               │
    ┌────▼─────┐                   ┌────▼──────┐
    │  Table   │                   │  Column   │
    │ Lineage  │                   │  Lineage  │
    │Extractor │                   │ Extractor │
    └────┬─────┘                   └────┬──────┘
         │                               │
         └───────────┬───────────────────┘
                     │
            ┌────────▼─────────┐
            │   ZetaSQL        │
            │   Analyzer       │
            └────────┬─────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    ┌────▼──────┐         ┌─────▼────────┐
    │  BigQuery │         │   Sample     │
    │  Options  │         │   Catalog    │
    └───────────┘         └──────────────┘
```

## 패키지 구조

```
src/zetasql_demo/
├── __init__.py                  # 패키지 초기화
├── catalog/
│   ├── __init__.py
│   └── sample_catalog.py        # 샘플 카탈로그 생성
├── options/
│   ├── __init__.py
│   └── bigquery_options.py      # BigQuery LanguageOptions
├── lineage/
│   ├── __init__.py
│   ├── models.py                # 데이터 모델 (dataclass)
│   ├── table_lineage.py         # 테이블 리니지 추출
│   ├── column_lineage.py        # 컬럼 리니지 추출
│   └── formatters.py            # 결과 포맷팅
└── examples/
    ├── demo_table_lineage.py    # 테이블 리니지 시연
    └── demo_column_lineage.py   # 컬럼 리니지 시연
```

## 클래스 설계

### 1. 데이터 모델 (models.py)

#### TableEntity
```python
@dataclass(frozen=True)
class TableEntity:
    """테이블 엔티티"""
    name: str  # 전체 테이블명 (예: "project.dataset.table")
    
    @property
    def simple_name(self) -> str:
        """마지막 부분만 반환 (예: "table")"""
```

#### ColumnEntity
```python
@dataclass(frozen=True)
class ColumnEntity:
    """컬럼 엔티티"""
    table: str   # 전체 테이블명
    column: str  # 컬럼명
    
    def __str__(self) -> str:
        return f"{self.table}.{self.column}"
```

#### TableLineage
```python
@dataclass
class TableLineage:
    """테이블 레벨 리니지"""
    target_table: TableEntity | None  # 타겟 테이블 (SELECT는 None)
    source_tables: set[TableEntity]   # 소스 테이블들
    statement_type: str               # SQL 문 타입
```

#### ColumnLineage
```python
@dataclass
class ColumnLineage:
    """컬럼 레벨 리니지"""
    target: ColumnEntity              # 타겟 컬럼
    parents: set[ColumnEntity]        # 부모(소스) 컬럼들
```

### 2. 카탈로그 생성 (catalog/sample_catalog.py)

#### create_sample_catalog()
```python
def create_sample_catalog() -> SimpleCatalog:
    """
    BigQuery 스타일 샘플 카탈로그 생성
    
    Tables:
    - myproject.sales.orders (order_id, customer_id, product_id, quantity, amount, order_date)
    - myproject.sales.customers (customer_id, name, email, country)
    - myproject.sales.products (product_id, name, price, category)
    - myproject.analytics.order_summary (생성 대상 테이블 - 스키마 미리 정의)
    
    Returns:
        SimpleCatalog with builtin functions
    """
```

#### get_language_options()
```python
def get_language_options() -> LanguageOptions:
    """
    BigQuery 호환 LanguageOptions 반환
    
    Returns:
        LanguageOptions with maximum features
    """
```

### 3. BigQuery 옵션 (options/bigquery_options.py)

#### get_bigquery_language_options()
```python
def get_bigquery_language_options() -> LanguageOptions:
    """
    BigQuery SQL 방언에 맞는 LanguageOptions 생성
    
    Java의 BigQueryLanguageOptions.java 포팅:
    - ProductMode.PRODUCT_EXTERNAL
    - 80+ 언어 기능 활성화
    - Statement kinds 설정
    
    Returns:
        Configured LanguageOptions
    """
```

### 4. 테이블 리니지 추출 (lineage/table_lineage.py)

#### TableLineageExtractor (ResolvedNodeVisitor)
```python
class TableLineageExtractor(ResolvedNodeVisitor):
    """
    Resolved AST를 순회하여 테이블 리니지 추출
    
    Attributes:
        source_tables: 발견된 소스 테이블들
        target_table: 타겟 테이블 (없으면 None)
        statement_type: SQL 문 타입
    """
    
    def __init__(self):
        """초기화"""
        
    def visit_ResolvedTableScan(self, node):
        """테이블 스캔 노드 방문 - 소스 테이블 수집"""
        
    def visit_ResolvedCreateTableAsSelectStmt(self, node):
        """CREATE TABLE AS SELECT 처리 - 타겟 테이블 설정"""
        
    def visit_ResolvedCreateViewStmt(self, node):
        """CREATE VIEW 처리 - 타겟 테이블(뷰) 설정"""
        
    def visit_ResolvedInsertStmt(self, node):
        """INSERT 처리 - 타겟 테이블 설정"""
        
    def visit_ResolvedUpdateStmt(self, node):
        """UPDATE 처리 - 타겟 테이블 설정"""
        
    def visit_ResolvedMergeStmt(self, node):
        """MERGE 처리 - 타겟 테이블 설정"""
```

#### extract_table_lineage()
```python
def extract_table_lineage(resolved_stmt: ResolvedStatement) -> TableLineage:
    """
    Resolved statement에서 테이블 리니지 추출
    
    Args:
        resolved_stmt: 분석된 SQL 문
        
    Returns:
        TableLineage 객체
    """
```

### 5. 컬럼 리니지 추출 (lineage/column_lineage.py)

#### ParentColumnFinder (ResolvedNodeVisitor)
```python
class ParentColumnFinder(ResolvedNodeVisitor):
    """
    컬럼의 terminal parent columns 찾기
    
    Java의 ParentColumnFinder.java 포팅:
    - BFS를 통한 컬럼 부모 트리 순회
    - Terminal columns (테이블에서 직접 읽는 컬럼) 추적
    
    Attributes:
        column_map: 컬럼 ID -> ResolvedColumn 매핑
        parent_map: 컬럼 ID -> 부모 컬럼 IDs 매핑
        terminal_columns: Terminal column IDs
    """
    
    def visit_ResolvedTableScan(self, node):
        """테이블 스캔 - terminal columns 등록"""
        
    def visit_ResolvedComputedColumn(self, node):
        """계산된 컬럼 - 부모 컬럼 추적"""
        
    def visit_ResolvedColumnRef(self, node):
        """컬럼 참조 - 부모 관계 기록"""
        
    def find_terminal_parents(self, column_id: int) -> set[int]:
        """BFS로 terminal parent 찾기"""
```

#### ColumnLineageExtractor (ResolvedNodeVisitor)
```python
class ColumnLineageExtractor(ResolvedNodeVisitor):
    """
    컬럼 레벨 리니지 추출
    
    Java의 ColumnLineageExtractor.java 포팅
    
    Attributes:
        lineages: 추출된 컬럼 리니지 목록
        parent_finder: ParentColumnFinder 인스턴스
    """
    
    def extract_for_query_stmt(self, stmt: ResolvedQueryStmt, target_table: str):
        """SELECT 문의 컬럼 리니지 추출"""
        
    def extract_for_create_table_as_select(self, stmt):
        """CREATE TABLE AS SELECT의 컬럼 리니지 추출"""
        
    def extract_for_insert(self, stmt):
        """INSERT의 컬럼 리니지 추출"""
        
    def extract_for_update(self, stmt):
        """UPDATE의 컬럼 리니지 추출"""
        
    def extract_for_merge(self, stmt):
        """MERGE의 컬럼 리니지 추출"""
```

#### extract_column_lineage()
```python
def extract_column_lineage(resolved_stmt: ResolvedStatement) -> list[ColumnLineage]:
    """
    Resolved statement에서 컬럼 리니지 추출
    
    Args:
        resolved_stmt: 분석된 SQL 문
        
    Returns:
        ColumnLineage 객체 리스트
    """
```

### 6. 결과 포맷팅 (lineage/formatters.py)

#### LineageFormatter
```python
class LineageFormatter:
    """리니지 결과 포맷팅"""
    
    @staticmethod
    def table_lineage_to_json(lineage: TableLineage) -> str:
        """테이블 리니지를 JSON으로 변환"""
        
    @staticmethod
    def table_lineage_to_text(lineage: TableLineage) -> str:
        """테이블 리니지를 읽기 쉬운 텍스트로 변환"""
        
    @staticmethod
    def column_lineage_to_json(lineages: list[ColumnLineage]) -> str:
        """컬럼 리니지를 JSON으로 변환"""
        
    @staticmethod
    def column_lineage_to_text(lineages: list[ColumnLineage]) -> str:
        """컬럼 리니지를 읽기 쉬운 텍스트로 변환"""
```

## Visitor 패턴 설계

### ResolvedNodeVisitor 사용 전략

1. **동적 메서드 디스패치**: `visit_{NodeType}` 메서드를 통해 노드 타입별 처리
2. **MRO 기반 탐색**: 가장 구체적인 타입부터 찾아서 처리
3. **descend()로 자식 순회**: 명시적으로 자식 노드 방문 제어
4. **default_visit() 폴백**: 처리되지 않은 노드는 기본 동작 수행

### 예제: TableLineageExtractor
```python
class TableLineageExtractor(ResolvedNodeVisitor):
    def __init__(self):
        super().__init__()
        self.source_tables = set()
        self.target_table = None
    
    # 특정 노드 타입 처리
    def visit_ResolvedTableScan(self, node):
        # 테이블 정보 추출
        if node.table:
            table_name = node.table.name
            self.source_tables.add(TableEntity(table_name))
        # 자식 노드 계속 순회
        self.descend(node)
    
    # 기본 동작: 모든 자식 노드 방문
    def default_visit(self, node):
        self.descend(node)
```

## 알고리즘 설계

### 테이블 리니지 추출 알고리즘

```
1. ResolvedStatement를 입력으로 받음
2. TableLineageExtractor 인스턴스 생성
3. Statement 타입에 따라 타겟 테이블 설정:
   - ResolvedCreateTableAsSelectStmt → table_name_path
   - ResolvedCreateViewStmt → name_path
   - ResolvedInsertStmt → table_scan.table
   - ResolvedUpdateStmt → table_scan.table
   - ResolvedMergeStmt → table_scan.table
4. 전체 AST를 순회하며 ResolvedTableScan 노드 수집
5. TableLineage 객체 반환 (target_table, source_tables, statement_type)
```

### 컬럼 리니지 추출 알고리즘

```
1. ResolvedStatement를 입력으로 받음
2. ParentColumnFinder로 전체 AST 순회:
   a. ResolvedTableScan에서 terminal columns 등록
   b. ResolvedComputedColumn에서 계산된 컬럼과 부모 관계 추적
   c. ResolvedColumnRef에서 컬럼 참조 기록
   d. 컬럼 ID 기반 parent 매핑 구축
3. Statement 타입별 output columns 추출:
   - SELECT: output_column_list
   - CREATE TABLE AS SELECT: output_column_list
   - INSERT: insert_column_list
   - UPDATE: update_item_list의 target columns
   - MERGE: merge_when_clause의 update/insert columns
4. 각 output column에 대해:
   a. ParentColumnFinder.find_terminal_parents() 호출
   b. Terminal parent IDs → ColumnEntity 변환
   c. ColumnLineage 객체 생성 (target, parents)
5. ColumnLineage 객체 리스트 반환
```

## 에러 처리 전략

### 원칙
- 에러 처리 테스트는 작성하지 않음
- 정상 경로(happy path)에 집중
- 예외 발생 시 그대로 전파하여 사용자에게 보여줌

### 예외 상황
1. **분석 실패**: ZetaSQL Analyzer가 던지는 예외를 그대로 전파
2. **지원되지 않는 노드**: Visitor의 default_visit()에서 자동 처리
3. **누락된 속성**: AttributeError가 발생하면 그대로 전파

## 테스트 전략

### 단위 테스트 구조
```
tests/
├── conftest.py              # 공통 fixture (catalog, analyzer)
├── test_catalog.py          # 카탈로그 생성 테스트
├── test_bigquery_options.py # BigQuery 옵션 테스트
├── test_table_lineage.py    # 테이블 리니지 테스트
├── test_column_lineage.py   # 컬럼 리니지 테스트
└── test_formatters.py       # 포맷터 테스트
```

### TDD 사이클
1. **Red**: 테스트 작성 (실패)
2. **Green**: 최소 구현 (통과)
3. **Refactor**: 코드 개선

### 테스트 범위
- 모든 지원 SQL 문법 (SELECT, CREATE, INSERT, UPDATE, MERGE)
- 복잡한 쿼리 (서브쿼리, CTE, 윈도우 함수)
- JOIN (INNER, LEFT, RIGHT, FULL)
- 다양한 표현식 (산술, 함수, CASE)

## 성능 고려사항

### Visitor 패턴 최적화
- 메서드 디스패치 캐싱 (ResolvedNodeVisitor에 내장)
- 필드 메타데이터 캐싱 (ResolvedNodeVisitor에 내장)

### 메모리 관리
- 불필요한 AST 복사 방지
- Set을 사용하여 중복 제거

### 확장성
- 모듈화된 구조로 새로운 SQL 문법 추가 용이
- Visitor 패턴으로 새로운 노드 타입 처리 추가 용이
