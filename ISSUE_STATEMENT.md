# Issue Statement

## Problem

Modern LLMs can often surface domain-relevant concepts even at relatively small model sizes, yet they still fail through poor selection, premature closure, weak reframing, and unstable control of competing hypotheses.

The central unresolved question is therefore not simply whether an LLM can generate a useful candidate, but where the performance loss first appears in the reasoning/control pipeline.

## Primary hypothesis

A lightweight LLM may already provide sufficiently broad domain-semantic candidate coverage for many tasks. A significant share of downstream failure may instead arise from candidate scoring, pruning, branch selection, contradiction handling, reframing, and closure control.

## Research question

Given identical intermediate representations and candidate sets, where does measurable divergence first arise between:

- LLM self-selection / self-control,
- deterministic EC-style selection / control,
- and Oracle substitutions?

## Secondary questions

1. Does model size materially improve candidate recall, or mainly affect ranking/selection?
2. If candidate recall is already high for a lightweight LLM, can deterministic EC recover performance by improving selection and control?
3. Which is the smallest architectural sublayer where LLM behavior remains materially superior?
4. What is the largest contiguous downstream region that can be replaced by deterministic EC without material loss?
5. Are failures caused by missing semantic content, wrong ranking, wrong branch choice, missed reframing, or false closure?

## Non-goal

This study does not assume that an LLM performs explicit semantic search internally. Token continuation is treated only as one mechanism for producing observable candidate continuations. The experiment evaluates externally measurable intermediate artifacts and decisions, not unverifiable internal reasoning narratives.

## Experimental claim discipline

A layer may only be identified as a bottleneck when upstream inputs are held constant and substitution at that layer changes downstream performance. End-to-end score differences alone are insufficient for causal attribution.