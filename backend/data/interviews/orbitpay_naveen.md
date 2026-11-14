---
id: interview-orbitpay-naveen
doc_type: interview
title: OrbitPay Fintech interview experience - Naveen J. (CSE, 2026 batch, selected)
company_id: orbitpay
---

# OrbitPay Fintech interview experience - Naveen J. (CSE, 2026 batch, selected)

(Fictional sample write-up.)

## Online Coding Test

Two medium problems and 15 multiple-choice questions in 90 minutes. Problems: top k frequent elements (heap or bucket sort) and validating a sequence of transactions against a balance (simulation with a hash map). The MCQs on SQL were tricky; several were about NULL handling in aggregates.

## Technical Interview

The coding question was to design an LRU cache, which is a hash map plus a doubly linked list. Then SQL: write a query to find accounts whose total debits exceed total credits in the last 30 days.

Then came the part that is specific to a payments company. "A client calls our payment API, the network times out and they retry. How do you make sure the customer is not charged twice?" The answer they want is an idempotency key: the client sends a unique key, and the server stores the result against that key and returns the same result on a retry. He also asked what ACID means with a money-transfer example.

## System Design Basics Round

Design a wallet service: add money, pay and view history. I drew the APIs, two tables (wallets and transactions) and explained why the balance update and the transaction insert must be in one database transaction. He asked what happens if the service crashes midway.

## HR Interview

Relocation to Mumbai and expected joining date.

## Tips

- Read about idempotency, retries and database transactions. Every interviewer here asks about them.
- For design, start with the API and the tables. Keep it simple.
