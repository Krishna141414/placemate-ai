---
id: guide-system-design
doc_type: guide
title: System Design Basics Guide
---

# System Design Basics Guide

(Fictional sample guide written for the KRIT placement cell.)

## What freshers are asked

Campus interviews do not expect you to design a global platform. Dream category companies ask a small design question to see how you think: a URL shortener, a parking lot, a rate limiter, a wallet or a notification service. There are two flavours:

- **Low-level design:** classes, their responsibilities and relationships. Asked as "design a parking lot" or "design a library system".
- **High-level design basics:** the main components of a service, its APIs, its data and what happens when something fails.

## A structure that works for any question

1. **Clarify.** Ask who uses it, what the main actions are and what scale to assume. Spend the first five minutes here.
2. **List the requirements.** Three or four functional ones, and one or two non-functional ones such as "must not lose data".
3. **Define the APIs.** For example: create a short link, open a short link.
4. **Design the data.** Which tables or collections, which keys, which indexes.
5. **Draw the components.** Client, server, database, and a cache or queue only if you can say why it is needed.
6. **Discuss failures and limits.** What if the server crashes midway? What if the same request arrives twice? Where would this design break first?

## Concepts to know

- Client and server, HTTP methods and status codes, REST.
- SQL versus NoSQL in one or two sentences each.
- Indexes and why they speed up reads but slow down writes.
- Caching: what to cache and when it becomes stale.
- Load balancer: what it does.
- Message queue: why work is done in the background.
- Idempotency: making a retried request safe, usually with a unique key.
- Database transactions and ACID.
- Horizontal versus vertical scaling.

## For low-level design

Identify the nouns in the problem: they usually become classes. Give each class one job. Prefer composition over deep inheritance. Know the SOLID principles well enough to give one example of each, and two or three patterns such as singleton, factory and observer.

## Three-week plan

- **Week 1:** Concepts above, one a day, written in your own words.
- **Week 2:** Low-level design of a parking lot, library, vending machine and rate limiter. Write the classes in code.
- **Week 3:** High-level basics of a URL shortener, wallet, notification service and chat app. Practise explaining each in 15 minutes to a friend.

## Common mistakes

- Starting to draw or code before asking a single question.
- Using terms such as microservices or sharding without being able to explain them.
- Ignoring failure cases.
- Staying silent while thinking. Say what you are considering.
