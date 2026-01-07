# Java 참고 자료 (Java Reference)

## GoogleCloudPlatform/zetasql-toolkit 레포지토리

**Repository**: https://github.com/GoogleCloudPlatform/zetasql-toolkit

## 포팅 대상 Java 파일 상세

### 1. BigQueryLanguageOptions.java

**경로**: `zetasql-toolkit-bigquery/src/main/java/com/google/zetasql/toolkit/options/BigQueryLanguageOptions.java`

**GitHub URL**: https://github.com/GoogleCloudPlatform/zetasql-toolkit/blob/main/zetasql-toolkit-bigquery/src/main/java/com/google/zetasql/toolkit/options/BigQueryLanguageOptions.java

**핵심 내용**:
```java
public class BigQueryLanguageOptions {
  
  private static final LanguageOptions BIGQUERY_LANGUAGE_OPTIONS = createLanguageOptions();
  
  public static LanguageOptions get() {
    return BIGQUERY_LANGUAGE_OPTIONS;
  }
  
  private static LanguageOptions createLanguageOptions() {
    LanguageOptions options = new LanguageOptions();
    
    // Product mode
    options.setProductMode(ProductMode.PRODUCT_EXTERNAL);
    options.setNameResolutionMode(NameResolutionMode.NAME_RESOLUTION_DEFAULT);
    
    // Enable 80+ language features
    options.enableLanguageFeature(LanguageFeature.FEATURE_V_1_1_SELECT_STAR_EXCEPT_REPLACE);
    options.enableLanguageFeature(LanguageFeature.FEATURE_V_1_1_ORDER_BY_COLLATE);
    options.enableLanguageFeature(LanguageFeature.FEATURE_V_1_1_CAST_DIFFERENT_ARRAY_TYPES);
    // ... (80+ features)
    
    // Supported statement kinds
    options.setSupportedStatementKinds(ImmutableSet.of(
        ResolvedNodeKind.RESOLVED_QUERY_STMT,
        ResolvedNodeKind.RESOLVED_INSERT_STMT,
        ResolvedNodeKind.RESOLVED_UPDATE_STMT,
        ResolvedNodeKind.RESOLVED_MERGE_STMT,
        ResolvedNodeKind.RESOLVED_CREATE_TABLE_AS_SELECT_STMT,
        // ... more statement kinds
    ));
    
    // Enable reservable keywords
    options.enableReservableKeyword("QUALIFY");
    
    return options;
  }
}
```

**주요 활성화 기능**:
- QUALIFY
- PIVOT / UNPIVOT
- JSON functions
- GEOGRAPHY types
- NUMERIC / BIGNUMERIC types
- Window functions
- WITH (CTE)
- Array functions
- Struct operations
- Date/Time functions

---

### 2. ColumnLineageExtractor.java

**경로**: `zetasql-toolkit-core/src/main/java/com/google/zetasql/toolkit/tools/lineage/ColumnLineageExtractor.java`

**GitHub URL**: https://github.com/GoogleCloudPlatform/zetasql-toolkit/blob/main/zetasql-toolkit-core/src/main/java/com/google/zetasql/toolkit/tools/lineage/ColumnLineageExtractor.java

**핵심 로직**:
```java
public class ColumnLineageExtractor {
  
  // Extract lineage for CREATE TABLE AS SELECT
  public static Set<ColumnLineage> extractColumnLevelLineage(
      ResolvedCreateTableAsSelectStmt stmt) {
    String outputTable = String.join(".", stmt.getNamePath());
    return extractColumnLevelLineage(stmt.getQuery(), outputTable);
  }
  
  // Extract lineage for INSERT
  public static Set<ColumnLineage> extractColumnLevelLineage(
      ResolvedInsertStmt stmt) {
    String outputTable = stmt.getTableScan().getTable().getFullName();
    
    Set<ColumnLineage> lineages = new HashSet<>();
    List<ResolvedColumn> insertColumns = stmt.getInsertColumnList();
    
    // Map each insert column to its parent columns
    for (int i = 0; i < insertColumns.size(); i++) {
      ResolvedColumn targetColumn = insertColumns.get(i);
      ResolvedColumn queryColumn = stmt.getQuery().getOutputColumnList().get(i);
      
      Set<ColumnEntity> parents = ParentColumnFinder.findParentsForColumn(
          stmt.getQuery(), queryColumn);
      
      ColumnEntity target = new ColumnEntity(outputTable, targetColumn.getName());
      lineages.add(new ColumnLineage(target, parents));
    }
    
    return lineages;
  }
  
  // Extract lineage for UPDATE
  public static Set<ColumnLineage> extractColumnLevelLineage(
      ResolvedUpdateStmt stmt) {
    String outputTable = stmt.getTableScan().getTable().getFullName();
    
    Set<ColumnLineage> lineages = new HashSet<>();
    
    for (ResolvedUpdateItem updateItem : stmt.getUpdateItemList()) {
      ResolvedColumn targetColumn = updateItem.getTarget();
      ResolvedExpr setValueExpr = updateItem.getSetValue();
      
      Set<ColumnEntity> parents = ParentColumnFinder.findParentsForExpression(
          stmt, setValueExpr);
      
      ColumnEntity target = new ColumnEntity(outputTable, targetColumn.getName());
      lineages.add(new ColumnLineage(target, parents));
    }
    
    return lineages;
  }
  
  // Extract lineage for MERGE
  public static Set<ColumnLineage> extractColumnLevelLineage(
      ResolvedMergeStmt stmt) {
    String outputTable = stmt.getTableScan().getTable().getFullName();
    
    Set<ColumnLineage> lineages = new HashSet<>();
    
    for (ResolvedMergeWhen whenClause : stmt.getWhenClauseList()) {
      // Handle UPDATE actions
      if (whenClause.getActionType() == MergeActionType.UPDATE) {
        for (ResolvedUpdateItem updateItem : whenClause.getUpdateItemList()) {
          // Similar to UPDATE logic
        }
      }
      // Handle INSERT actions
      else if (whenClause.getActionType() == MergeActionType.INSERT) {
        // Similar to INSERT logic
      }
    }
    
    return lineages;
  }
  
  // Extract lineage for SELECT / CREATE VIEW
  private static Set<ColumnLineage> extractColumnLevelLineage(
      ResolvedQueryStmt query, String outputTable) {
    
    Set<ColumnLineage> lineages = new HashSet<>();
    
    for (ResolvedOutputColumn outputColumn : query.getOutputColumnList()) {
      ResolvedColumn column = outputColumn.getColumn();
      
      Set<ColumnEntity> parents = ParentColumnFinder.findParentsForColumn(
          query, column);
      
      ColumnEntity target = new ColumnEntity(outputTable, outputColumn.getName());
      lineages.add(new ColumnLineage(target, parents));
    }
    
    return lineages;
  }
}
```

**처리 흐름**:
1. Statement 타입 확인
2. 타겟 테이블 및 컬럼 추출
3. 각 타겟 컬럼에 대해 `ParentColumnFinder` 호출
4. `ColumnLineage` 객체 생성

---

### 3. ParentColumnFinder.java

**경로**: `zetasql-toolkit-core/src/main/java/com/google/zetasql/toolkit/tools/lineage/ParentColumnFinder.java`

**GitHub URL**: https://github.com/GoogleCloudPlatform/zetasql-toolkit/blob/main/zetasql-toolkit-core/src/main/java/com/google/zetasql/toolkit/tools/lineage/ParentColumnFinder.java

**핵심 알고리즘**:
```java
public class ParentColumnFinder {
  
  // Find terminal parent columns for a given column
  public static Set<ColumnEntity> findParentsForColumn(
      ResolvedStatement stmt, ResolvedColumn column) {
    
    ParentColumnFinder finder = new ParentColumnFinder();
    finder.visit(stmt);  // Build column parent map
    
    return finder.getTerminalParents(column.getId());
  }
  
  // Find terminal parent columns for an expression
  public static Set<ColumnEntity> findParentsForExpression(
      ResolvedStatement stmt, ResolvedExpr expr) {
    
    ParentColumnFinder finder = new ParentColumnFinder();
    finder.visit(stmt);
    
    Set<Integer> directParents = DirectParentColumnFinder.find(expr);
    Set<ColumnEntity> terminalParents = new HashSet<>();
    
    for (Integer columnId : directParents) {
      terminalParents.addAll(finder.getTerminalParents(columnId));
    }
    
    return terminalParents;
  }
  
  private Map<Integer, ResolvedColumn> columnMap;      // column ID → column
  private Map<Integer, Set<Integer>> parentMap;         // column ID → parent IDs
  private Set<Integer> terminalColumns;                 // terminal column IDs
  
  private ParentColumnFinder() {
    this.columnMap = new HashMap<>();
    this.parentMap = new HashMap<>();
    this.terminalColumns = new HashSet<>();
  }
  
  // Visit ResolvedTableScan - register terminal columns
  @Override
  public void visit(ResolvedTableScan scan) {
    for (ResolvedColumn column : scan.getColumnList()) {
      columnMap.put(column.getId(), column);
      terminalColumns.add(column.getId());
      parentMap.put(column.getId(), new HashSet<>());
    }
    super.visit(scan);
  }
  
  // Visit ResolvedComputedColumn - track parent relationships
  @Override
  public void visit(ResolvedComputedColumn computedColumn) {
    ResolvedColumn column = computedColumn.getColumn();
    columnMap.put(column.getId(), column);
    
    // Find direct parents in the expression
    Set<Integer> parents = DirectParentColumnFinder.find(computedColumn.getExpr());
    parentMap.put(column.getId(), parents);
    
    super.visit(computedColumn);
  }
  
  // BFS to find terminal parents
  private Set<ColumnEntity> getTerminalParents(Integer columnId) {
    Set<ColumnEntity> result = new HashSet<>();
    Queue<Integer> queue = new LinkedList<>();
    Set<Integer> visited = new HashSet<>();
    
    queue.add(columnId);
    visited.add(columnId);
    
    while (!queue.isEmpty()) {
      Integer current = queue.poll();
      
      if (terminalColumns.contains(current)) {
        // Found a terminal column
        ResolvedColumn col = columnMap.get(current);
        result.add(new ColumnEntity(col.getTableName(), col.getName()));
      } else {
        // Continue searching parents
        Set<Integer> parents = parentMap.getOrDefault(current, new HashSet<>());
        for (Integer parent : parents) {
          if (!visited.contains(parent)) {
            queue.add(parent);
            visited.add(parent);
          }
        }
      }
    }
    
    return result;
  }
}
```

**알고리즘 설명**:
1. **AST 순회**: 모든 노드를 방문하여 컬럼 관계 맵 구축
2. **Terminal Columns**: `ResolvedTableScan`에서 직접 읽는 컬럼들
3. **Computed Columns**: 표현식으로 계산된 컬럼들, 부모 컬럼 추적
4. **BFS**: 주어진 컬럼에서 시작하여 terminal columns까지 역추적

---

### 4. DirectParentColumnFinder.java

**경로**: `zetasql-toolkit-core/src/main/java/com/google/zetasql/toolkit/tools/lineage/DirectParentColumnFinder.java`

**핵심 로직**:
```java
public class DirectParentColumnFinder {
  
  // Find direct parent column IDs in an expression
  public static Set<Integer> find(ResolvedExpr expr) {
    DirectParentColumnFinder finder = new DirectParentColumnFinder();
    finder.visit(expr);
    return finder.getParentColumnIds();
  }
  
  private Set<Integer> parentColumnIds = new HashSet<>();
  
  @Override
  public void visit(ResolvedColumnRef columnRef) {
    parentColumnIds.add(columnRef.getColumn().getId());
    super.visit(columnRef);
  }
  
  @Override
  public void visit(ResolvedFunctionCall functionCall) {
    // Recursively visit arguments
    for (ResolvedExpr arg : functionCall.getArgumentList()) {
      visit(arg);
    }
    super.visit(functionCall);
  }
  
  @Override
  public void visit(ResolvedSubqueryExpr subquery) {
    // Handle subquery references
    super.visit(subquery);
  }
  
  // ... handle other expression types
}
```

---

### 5. ColumnEntity.java

**경로**: `zetasql-toolkit-core/src/main/java/com/google/zetasql/toolkit/tools/lineage/ColumnEntity.java`

```java
public class ColumnEntity {
  private final String table;
  private final String name;
  
  public ColumnEntity(String table, String name) {
    this.table = table;
    this.name = name;
  }
  
  // Getters, equals, hashCode, toString
}
```

**Python 포팅**: `@dataclass(frozen=True)` 사용

---

### 6. ColumnLineage.java

**경로**: `zetasql-toolkit-core/src/main/java/com/google/zetasql/toolkit/tools/lineage/ColumnLineage.java`

```java
public class ColumnLineage {
  private final ColumnEntity target;
  private final Set<ColumnEntity> parents;
  
  public ColumnLineage(ColumnEntity target, Set<ColumnEntity> parents) {
    this.target = target;
    this.parents = parents;
  }
  
  // Getters, equals, hashCode, toString
}
```

**Python 포팅**: `@dataclass` 사용

---

### 7. ExtractColumnLevelLineage.java (예제)

**경로**: `zetasql-toolkit-examples/src/main/java/com/google/zetasql/toolkit/examples/ExtractColumnLevelLineage.java`

**GitHub URL**: https://github.com/GoogleCloudPlatform/zetasql-toolkit/blob/main/zetasql-toolkit-examples/src/main/java/com/google/zetasql/toolkit/examples/ExtractColumnLevelLineage.java

**예제 SQL**:
```java
public class ExtractColumnLevelLineage {
  
  public static void main(String[] args) {
    // Create BigQuery catalog
    BigQueryCatalog catalog = BigQueryCatalog.usingBigQueryAPI("project-id");
    
    // Add required tables
    catalog.register(BigQueryTableRef.from("project.dataset.orders"));
    catalog.register(BigQueryTableRef.from("project.dataset.customers"));
    
    // Create analyzer
    AnalyzerOptions options = new AnalyzerOptions();
    options.setLanguageOptions(BigQueryLanguageOptions.get());
    
    ZetaSQLToolkitAnalyzer analyzer = new ZetaSQLToolkitAnalyzer(options);
    
    // Example 1: CREATE TABLE AS SELECT
    String sql1 = """
      CREATE TABLE project.dataset.order_summary AS
      SELECT 
        o.order_id,
        c.customer_name,
        o.amount * 1.1 as total_amount
      FROM project.dataset.orders o
      JOIN project.dataset.customers c ON o.customer_id = c.customer_id
    """;
    
    ResolvedStatement stmt1 = analyzer.analyzeStatements(sql1, catalog).get(0);
    Set<ColumnLineage> lineage1 = ColumnLineageExtractor.extractColumnLevelLineage(
        (ResolvedCreateTableAsSelectStmt) stmt1);
    
    System.out.println("Lineage for CREATE TABLE AS SELECT:");
    printLineage(lineage1);
    
    // Example 2: INSERT
    String sql2 = """
      INSERT INTO project.dataset.order_summary (order_id, customer_name, total_amount)
      SELECT order_id, customer_name, amount
      FROM project.dataset.orders
    """;
    
    ResolvedStatement stmt2 = analyzer.analyzeStatements(sql2, catalog).get(0);
    Set<ColumnLineage> lineage2 = ColumnLineageExtractor.extractColumnLevelLineage(
        (ResolvedInsertStmt) stmt2);
    
    System.out.println("\nLineage for INSERT:");
    printLineage(lineage2);
    
    // Example 3: UPDATE
    String sql3 = """
      UPDATE project.dataset.orders
      SET amount = amount * 1.1
      WHERE order_date > '2023-01-01'
    """;
    
    ResolvedStatement stmt3 = analyzer.analyzeStatements(sql3, catalog).get(0);
    Set<ColumnLineage> lineage3 = ColumnLineageExtractor.extractColumnLevelLineage(
        (ResolvedUpdateStmt) stmt3);
    
    System.out.println("\nLineage for UPDATE:");
    printLineage(lineage3);
    
    // Example 4: MERGE
    String sql4 = """
      MERGE project.dataset.orders T
      USING project.dataset.new_orders S
      ON T.order_id = S.order_id
      WHEN MATCHED THEN
        UPDATE SET amount = S.amount
      WHEN NOT MATCHED THEN
        INSERT (order_id, amount) VALUES (S.order_id, S.amount)
    """;
    
    ResolvedStatement stmt4 = analyzer.analyzeStatements(sql4, catalog).get(0);
    Set<ColumnLineage> lineage4 = ColumnLineageExtractor.extractColumnLevelLineage(
        (ResolvedMergeStmt) stmt4);
    
    System.out.println("\nLineage for MERGE:");
    printLineage(lineage4);
  }
  
  private static void printLineage(Set<ColumnLineage> lineages) {
    for (ColumnLineage lineage : lineages) {
      System.out.println("  " + lineage.getTarget() + " <- " + lineage.getParents());
    }
  }
}
```

---

## Python 포팅 참고사항

### Java vs Python API 차이점

| Java | Python | 비고 |
|------|--------|------|
| `stmt.getNamePath()` | `stmt.name_path` | 속성 접근 |
| `stmt.getQuery()` | `stmt.query` | 속성 접근 |
| `column.getId()` | `column.column_id` | 컬럼 ID |
| `column.getName()` | `column.name` | 컬럼 이름 |
| `ResolvedNodeKind.RESOLVED_QUERY_STMT` | `RESOLVED_QUERY_STMT` (상수) | Node kind |
| Visitor pattern | `ResolvedNodeVisitor` 클래스 | 동일한 패턴 |
| `Set<ColumnLineage>` | `set[ColumnLineage]` | 집합 타입 |
| `List<ResolvedColumn>` | `list[ResolvedColumn]` | 리스트 타입 |

### 주요 Python API 사용

```python
from zetasql.api import Analyzer, ResolvedNodeVisitor
from zetasql.types import (
    AnalyzerOptions,
    LanguageOptions,
    SimpleCatalog,
    ResolvedStatement,
    ResolvedQueryStmt,
    ResolvedCreateTableAsSelectStmt,
    ResolvedInsertStmt,
    ResolvedUpdateStmt,
    ResolvedMergeStmt,
    ResolvedTableScan,
    ResolvedColumnRef,
    ResolvedComputedColumn,
)

# Visitor 패턴
class MyVisitor(ResolvedNodeVisitor):
    def visit_ResolvedTableScan(self, node):
        # Process table scan
        self.descend(node)  # Continue to children
    
    def default_visit(self, node):
        # Default behavior
        self.descend(node)
```

---

## 참고 링크

- **zetasql-toolkit GitHub**: https://github.com/GoogleCloudPlatform/zetasql-toolkit
- **ZetaSQL Documentation**: https://github.com/google/zetasql
- **Python zetasql package**: Installed at `.conda/lib/python3.14/site-packages/zetasql/`
