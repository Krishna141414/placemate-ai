---
id: guide-sql
doc_type: guide
title: SQL Preparation Guide
---

# SQL Preparation Guide

(Fictional sample guide written for the KRIT placement cell.)

## Why SQL

SQL is asked by software, analytics and services companies alike. It is also the fastest topic to become good at: two weeks of daily practice is enough for most campus interviews.

## Topics in order

1. SELECT, WHERE, ORDER BY, LIMIT and DISTINCT.
2. Aggregates: COUNT, SUM, AVG, MIN, MAX, with GROUP BY and HAVING.
3. Joins: INNER, LEFT, RIGHT, FULL and self joins.
4. Subqueries: in WHERE, in FROM, and correlated subqueries. EXISTS and NOT EXISTS.
5. Window functions: ROW_NUMBER, RANK, DENSE_RANK, LAG, LEAD, and running totals with SUM OVER.
6. NULL handling: IS NULL, COALESCE, and how aggregates ignore NULL.
7. Basics of design: primary key, foreign key, normalisation up to 3NF, and indexes.
8. Transactions: ACID properties and isolation levels (for product and fintech companies).

## Questions that come up every year

- Second highest salary, overall and per department.
- Employees who earn more than their manager (self join).
- Customers who never placed an order (LEFT JOIN with IS NULL, or NOT EXISTS).
- Top three products by revenue in each category (window function with PARTITION BY).
- Duplicate rows in a table (GROUP BY with HAVING COUNT greater than 1).
- Month-on-month growth (LAG).
- Running total of sales by date.

## WHERE versus HAVING

WHERE filters rows before grouping. HAVING filters groups after aggregation. A condition on an aggregate such as COUNT must go in HAVING.

## Two-week plan

- **Days 1 to 3:** Basic SELECT and aggregates. 10 queries a day.
- **Days 4 to 6:** Joins. Draw the tables on paper and predict the output before running the query.
- **Days 7 to 9:** Subqueries and EXISTS.
- **Days 10 to 12:** Window functions.
- **Days 13 to 14:** Schema design for a small system, such as a library or an online store, and mixed timed practice.

## How to practise

- Write queries by hand at least three times a week. Several companies ask for SQL on paper.
- Create your own small tables with 10 to 20 rows so you can check answers by eye.
- For each query, say aloud what each clause does. Interviewers ask you to explain, not just to write.

## Common mistakes

- Selecting a column that is neither grouped nor aggregated.
- Using INNER JOIN where rows without a match are needed.
- Forgetting that COUNT(column) skips NULL but COUNT(*) does not.
- Comparing with NULL using equals instead of IS NULL.
