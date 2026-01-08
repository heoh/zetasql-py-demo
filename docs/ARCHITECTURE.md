# 아키텍처 설계

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                    Examples Layer                        │
│  ┌────────────────────┐  ┌─────────────────────────┐   │
│  │ demo_table_lineage │  │ demo_column_lineage     │   │
│  └────────────────────┘  └─────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────┐
│                   Lineage Layer                          │
│  ┌──────────────────┐  ┌──────────────────────────┐    │
│  │ TableLineage     │  │ ColumnLineage            │    │
│  │ Extractor        │  │ Extractor                │    │
│  └──────────────────┘  └──────────────────────────┘    │
│          │                       │                       │
│          │              ┌────────┴────────┐             │
│          │              │                 │             │
│  ┌──────────────────┐  │  ┌─────────────────────────┐ │
│  │ ResolvedNode     │  │  │ ParentColumnFinder      │ │
│  │ Visitor          │  │  │ (Visitor)                │ │
│  └──────────────────┘  │  └─────────────────────────┘ │
│                        │  ┌─────────────────────────┐ │
│                        └──│ ExpressionParent        │ │
│                           │ Finder                   │ │
│                           └─────────────────────────┘ │
│  ┌────────────────────────────────────────────────┐   │
│  │ Formatters (JSON, Text)                        │   │
│  └────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────┐
│                 ZetaSQL Analysis Layer                   │
│  ┌────────────────────┐  ┌─────────────────────────┐   │
│  │ Analyzer           │  │ LanguageOptions         │   │
│  │                    │  │ (BigQuery)              │   │
│  └────────────────────┘  └─────────────────────────┘   │
│  ┌────────────────────┐                                 │
│  │ SimpleCatalog      │                                 │
│  │ (Tables)           │                                 │
│  └────────────────────┘                                 │
└─────────────────────────────────────────────────────────┘
```

## 모듈 설계

### 1. catalog/ - 카탈로그 생성 모듈

#### sample_catalog.py
```python
def create_sample_catalog() -> SimpleCatalog:
    """BigQuery 스타일 샘플 카탈로그 생성"""
    
def get_builtin_function_options() -> ZetaSQLBuiltinFunctionOptions:
    """Builtin 함수 옵션"""
```

**역할:**
- 테스트용 테이블 정의
- CatalogBuilder, TableBuilder 활용
- project.dataset.table 네이밍

### 2. options/ - 언어 옵션 모듈

#### bigquery_options.py
```python
def get_bigquery_language_options() -> LanguageOptions:
    """BigQuery 호환 LanguageOptions 반환"""
```

**Java 매핑:**
- `BigQueryLanguageOptions.java` 직접 포팅
- 80+ LanguageFeature 활성화
- ProductMode, NameResolutionMode 설정

### 3. lineage/ - 리니지 추출 핵심 모듈

#### models.py
```python
@dataclass
class ColumnEntity:
    table: str
    name: str
    
    @staticmethod
    def from_resolved_column(col: ResolvedColumn) -> ColumnEntity:
        """ResolvedColumn에서 생성"""

@dataclass
class ColumnLineage:
    target: ColumnEntity
    parents: Set[ColumnEntity]

@dataclass
class TableLineage:
    target: Optional[str]
    sources: Set[str]
    statement_type: str  # SELECT, INSERT, UPDATE, etc.
```

**Java 매핑:**
- `ColumnEntity.java`
- `ColumnLineage.java`

#### table_lineage.py
```python
class TableLineageExtractor(ResolvedNodeVisitor):
    """테이블 리니지 추출 Visitor"""
    
    def __init__(self):
        super().__init__()
        self.source_tables: Set[str] = set()
        self.target_table: Optional[str] = None
        
    def visit_ResolvedTableScan(self, node):
        """TableScan 노드 방문"""
        # node.table.name 추출
        
    def visit_ResolvedCreateTableAsSelectStmt(self, node):
        """CREATE TABLE AS SELECT 처리"""
        # target 설정
        
    def visit_ResolvedInsertStmt(self, node):
        """INSERT 처리"""
        
    def visit_ResolvedUpdateStmt(self, node):
        """UPDATE 처리"""
        
    def visit_ResolvedMergeStmt(self, node):
        """MERGE 처리"""

def extract_table_lineage(stmt: ResolvedStatement) -> TableLineage:
    """진입점 함수"""
```

**구현 전략:**
- ResolvedNodeVisitor 상속
- visit_ResolvedTableScan으로 소스 테이블 수집
- 각 statement 타입별 target 설정

#### column_lineage.py
```python
class ParentColumnFinder(ResolvedNodeVisitor):
    """컬럼의 terminal parent 찾기"""
    
    def __init__(self):
        super().__init__()
        self.columns_to_parents: Dict[str, List[ResolvedColumn]] = {}
        self.terminal_columns: Set[str] = set()
        self.with_entry_scopes: List[List[ResolvedWithEntry]] = []
        
    def visit_ResolvedComputedColumn(self, node):
        """ComputedColumn 등록"""
        
    def visit_ResolvedTableScan(self, node):
        """Terminal columns 등록"""
        
    def visit_ResolvedWithScan(self, node):
        """WITH 스코프 관리"""
        
    def visit_ResolvedWithRefScan(self, node):
        """WITH 참조 해결"""
        
    def find_terminal_parents(self, column: ResolvedColumn) -> List[ResolvedColumn]:
        """BFS로 terminal parents 찾기"""

class ExpressionParentFinder(ResolvedNodeVisitor):
    """표현식의 직접 parent 찾기"""
    
    def visit_ResolvedColumnRef(self, node):
        """컬럼 참조 수집"""
        
    def visit_ResolvedFunctionCall(self, node):
        """함수 인자의 parent"""
        
    def visit_ResolvedSubqueryExpr(self, node):
        """서브쿼리 처리"""

class ColumnLineageExtractor:
    """컬럼 리니지 추출"""
    
    @staticmethod
    def extract_for_create_table_as_select(stmt) -> Set[ColumnLineage]:
        """CREATE TABLE AS SELECT"""
        
    @staticmethod
    def extract_for_insert(stmt) -> Set[ColumnLineage]:
        """INSERT"""
        
    @staticmethod
    def extract_for_update(stmt) -> Set[ColumnLineage]:
        """UPDATE"""
        
    @staticmethod
    def extract_for_merge(stmt) -> Set[ColumnLineage]:
        """MERGE"""
```

**Java 매핑:**
- `ParentColumnFinder.java`
- `ExpressionParentFinder.java`
- `ColumnLineageExtractor.java`

**핵심 알고리즘:**
1. **AST 순회**: ResolvedStatement 전체를 방문하며 컬럼 관계 수집
2. **매핑 구축**: `columns_to_parents` 맵에 컬럼 ID → 직접 부모 컬럼들
3. **BFS 탐색**: 주어진 컬럼부터 BFS로 terminal columns까지 추적
4. **WITH 처리**: WITH entry 스코프 스택으로 CTE 참조 해결

#### formatters.py
```python
class LineageFormatter:
    """리니지 결과 포맷팅"""
    
    @staticmethod
    def to_json(lineages: Union[List[ColumnLineage], List[TableLineage]]) -> str:
        """JSON 형식 출력"""
        
    @staticmethod
    def to_text(lineages: Union[List[ColumnLineage], List[TableLineage]]) -> str:
        """텍스트 형식 출력"""
```

### 4. examples/ - 시연 스크립트

#### demo_table_lineage.py
```python
def main():
    # 1. 카탈로그 생성
    catalog = create_sample_catalog()
    
    # 2. Analyzer 설정
    lang_opts = get_bigquery_language_options()
    options = AnalyzerOptions(language_options=lang_opts)
    analyzer = Analyzer(options, catalog)
    
    # 3. 각 SQL 문법별 시연
    demo_select()
    demo_create_table_as_select()
    demo_insert()
    demo_update()
    demo_merge()
    
    # 4. 복잡한 쿼리 시연
    demo_subquery()
    demo_cte()
    demo_join()
```

#### demo_column_lineage.py
```python
def main():
    # Java ExtractColumnLevelLineage.java와 동일한 예제
    demo_create_table_as_select()
    demo_insert()
    demo_update()
    demo_merge()
```

## 데이터 플로우

### 테이블 리니지 추출 플로우
```
SQL Query
    │
    ▼
Analyzer.analyze_statement()
    │
    ▼
ResolvedStatement
    │
    ▼
TableLineageExtractor.visit()
    │
    ├─ visit_ResolvedTableScan() → 소스 테이블 수집
    │
    └─ visit_ResolvedXXXStmt() → 타겟 테이블 설정
    │
    ▼
TableLineage (target, sources)
    │
    ▼
LineageFormatter.to_json() / to_text()
```

### 컬럼 리니지 추출 플로우
```
SQL Query
    │
    ▼
Analyzer.analyze_statement()
    │
    ▼
ResolvedStatement
    │
    ▼
ColumnLineageExtractor.extract_xxx()
    │
    ├─ ResolvedOutputColumn 리스트 획득
    │
    └─ 각 output column에 대해:
        │
        ▼
    ParentColumnFinder.find_terminal_parents(column)
        │
        ├─ 1. AST 전체 순회 (visit)
        │     └─ columns_to_parents 맵 구축
        │
        └─ 2. BFS로 terminal parents 찾기
            │
            ▼
        List[ResolvedColumn] (terminal parents)
    │
    ▼
Set[ColumnLineage]
    │
    ▼
LineageFormatter.to_json() / to_text()
```

## Java to Python 매핑 가이드

### 클래스 매핑
| Java | Python |
|------|--------|
| `ResolvedNodes.Visitor` | `ResolvedNodeVisitor` |
| `HashMap<K, V>` | `Dict[K, V]` |
| `HashSet<T>` | `Set[T]` |
| `ArrayList<T>` | `List[T]` |
| `Optional<T>` | `Optional[T]` |
| `ImmutableList.of()` | `[]` or `tuple()` |
| `ImmutableSet.of()` | `set()` or `frozenset()` |
| `Stream API` | list comprehension, generator |

### 메서드 매핑
| Java | Python |
|------|--------|
| `column.getTableName()` | `column.table_name` |
| `column.getName()` | `column.name` |
| `column.getId()` | `column.column_id` |
| `stmt.getNamePath()` | `stmt.name_path` |
| `node.accept(visitor)` | `visitor.visit(node)` |
| `String.join(".", list)` | `".".join(list)` |

### Visitor 패턴
```java
// Java
public void visit(ResolvedTableScan scan) {
    // logic
}
```

```python
# Python
def visit_ResolvedTableScan(self, node):
    # logic
    self.descend(node)  # 자식 노드 방문
```

### WITH 스코프 처리
```java
// Java
private final Stack<List<ResolvedWithEntry>> withEntryScopes = new Stack<>();

public void visit(ResolvedWithScan scan) {
    withEntryScopes.push(scan.getWithEntryList());
    // ...
    withEntryScopes.pop();
}
```

```python
# Python
def __init__(self):
    self.with_entry_scopes: List[List[ResolvedWithEntry]] = []

def visit_ResolvedWithScan(self, node):
    self.with_entry_scopes.append(node.with_entry_list)
    self.descend(node)
    self.with_entry_scopes.pop()
```

## 테스트 전략

### 단위 테스트
- 각 visitor 메서드 독립 테스트
- Mock ResolvedNode 사용

### 통합 테스트
- 실제 SQL 쿼리 분석
- End-to-end 검증

### Fixture 구조
```python
# conftest.py
@pytest.fixture
def sample_catalog():
    return create_sample_catalog()

@pytest.fixture
def analyzer(sample_catalog):
    lang_opts = get_bigquery_language_options()
    options = AnalyzerOptions(language_options=lang_opts)
    return Analyzer(options, sample_catalog)
```

## 확장성 고려사항

### 향후 추가 가능 기능
1. **더 많은 SQL 방언 지원** (Spanner, PostgreSQL)
2. **시각화** (그래프 형태의 리니지)
3. **CLI 인터페이스**
4. **성능 최적화** (대용량 쿼리 처리)
5. **증분 분석** (변경된 부분만 재분석)
