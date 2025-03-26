# Comprehensive Spring Boot Application Analysis

## Application Context
{insert relevant high-level application summary}

## Components Relevant to Analysis
{insert summaries of the 3-5 most relevant components}

## API Flows Related to Analysis
{insert API flow data for endpoints relevant to the analysis}

## Component Relationship Matrix
{insert relevant portion of component relationship matrix}

## Analysis Requests
### General Query
{insert specific question}

### Feature Implementation
{insert feature description}

### Code Change Impact
{insert description of proposed code change}

## Analysis Instructions

### 1. General Query Analysis
1. Analyze the question in relation to the provided Spring Boot application context
2. Provide a detailed technical response addressing the question
3. Cite specific code files and components in your answer using the format [FileName.java]
4. Identify any potential impacts or considerations across components

### 2. Feature Implementation Analysis
1. Analyze how the requested feature would be implemented in this Spring Boot application
2. Identify which existing components would need to be modified
3. Specify any new components that would need to be created
4. Describe the changes required to each component
5. Identify potential challenges or considerations for implementation

### 3. Code Change Impact Analysis
1. Analyze the impact of the proposed change on the Spring Boot application
2. Identify all components that would be directly affected by the change
3. Identify all components that would be indirectly affected through dependencies
4. Assess the scope of the change (isolated vs. widespread)
5. Identify potential risks or considerations

## Response Format

### General Query Response
Provide a detailed technical response to the query, citing specific code files and components using the format [FileName.java]. Include any relevant code examples, architectural considerations, and potential limitations.

### Feature Implementation Response
```
Implementing [Feature Name] would require:

1. Modifications to existing components:
   - [ExistingComponent1.java]: {specific changes}
   - [ExistingComponent2.java]: {specific changes}

2. New components needed:
   - [NewComponent1.java]: {purpose and functionality}
   - [NewComponent2.java]: {purpose and functionality}

3. Implementation steps:
   {step-by-step implementation plan}

4. Potential challenges:
   {list of challenges and considerations}
```

### Code Change Impact Response
```
Changing [Component] would impact:

1. Direct impacts:
   - [Component1.java]: {specific impact}
   - [Component2.java]: {specific impact}

2. Indirect impacts (through dependencies):
   - [Component3.java] depends on [Component1.java]: {specific impact}
   - [Component4.java] uses [Component2.java]: {specific impact}

3. Scope assessment:
   {assessment of whether the change is isolated or widespread}

4. Risks and considerations:
   {list of risks and considerations}
```
