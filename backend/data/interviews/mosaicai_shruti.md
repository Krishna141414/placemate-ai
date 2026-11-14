---
id: interview-mosaicai-shruti
doc_type: interview
title: Mosaic AI Works interview experience - Shruti A. (CSE, 2026 batch, selected)
company_id: mosaicai
---

# Mosaic AI Works interview experience - Shruti A. (CSE, 2026 batch, selected)

(Fictional sample write-up.)

## Online Assessment

Sixty minutes of multiple-choice questions: Python output questions, probability (conditional probability and Bayes' rule), and machine learning basics such as what regularisation does and when accuracy is a bad metric.

## ML Take-home Task

We got a tabular dataset of insurance claims with a label for whether the claim was flagged. The class was imbalanced: only about 8 percent of claims were flagged. I split the data before doing any preprocessing, tried logistic regression and a gradient boosting model, and reported precision, recall and the confusion matrix instead of accuracy.

In my write-up I included a section called "where the model is wrong", with five misclassified examples and my guess about why. In the interview they said most submissions only reported a score.

## Technical Interview

- Explain bias and variance with an example from my own task.
- Why should you split the data before scaling? (To avoid leakage from the test set.)
- Precision versus recall: which matters more for flagging suspicious claims, and why?
- pandas: group by a column and compute the mean of another; NumPy: what broadcasting is.
- How would you know the model has become worse after deployment?

## Founder Round

I talked about a paper on document layout models that I had read for my project. He mostly wanted to see whether I had understood it or only read the abstract.

## Tips

- With imbalanced data, never report only accuracy.
- Write the take-home report as if a busy person will read only that.
- The first six months are an internship. Ask about the conversion criteria; they answer openly.
