# Self-Correction Review

## Original Response
{insert original LLM response}

## Application Context
{insert relevant high-level application summary}

## Component Relationship Matrix
{insert relevant portion of component relationship matrix}

## Instructions
Review the original response and verify:
1. Are all cited files actually mentioned in the application context?
2. Are the described relationships between components consistent with the provided component relationship matrix?
3. Are the described API flows consistent with the provided API flow data?
4. Does the impact analysis consider all dependent components from the relationship matrix?
5. Correct any inconsistencies and explain the corrections.

## Example Response Format:
```
Review of original response:

1. File reference accuracy:
   - [CorrectReference.java]: Verified in application context
   - [IncorrectReference.java]: Not found in application context, should be [CorrectFile.java]

2. Component relationship accuracy:
   - [Component1.java] correctly identified as depending on [Component2.java]
   - [Component3.java] incorrectly described as using [Component4.java], no such relationship exists

3. API flow accuracy:
   - The described flow for [/api/endpoint] is consistent with the API flow data
   - The described flow for [/api/another] is inconsistent, should include [MissingComponent.java]

4. Impact analysis completeness:
   - [MissingDependentComponent.java] was not considered but would be affected

Corrected response:
{insert corrected response}
```
