---
id: ts_type_2322
language: TypeScript
code: TS2322
category: Type System
severity: Compiler Error
title: Type is not assignable to type
description: A value does not satisfy the declared target type. Preserve the type contract or explicitly transform the value before assignment.
version_introduced: 1.0
source_reference: https://www.typescriptlang.org/docs/handbook/2/everyday-types.html
tier: 1
frequency: Common
situational_context: API parsing, strict mode
interaction_types: static typing
related_errors: cs_cs0029, py_typeerror
---

## Broken

```ts
let count: number = "12";
```

## Fixed

```ts
let count: number = Number("12");
```
