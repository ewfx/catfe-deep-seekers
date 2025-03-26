# Component Relationship Matrix

| Component | Depends On | Used By |
|-----------|-----------|--------|
| ACCOUNT_NUMBER_PATTERN_STRING |  | CodeGenerator |
| ACTION |  | TransactionRestController, TransactionService |
| Account |  | AccountRepository, AccountRestController, AccountService, TransactionRestController, TransactionService |
| AccountInput |  | AccountRestController |
| AccountRepository | Account | AccountService, TransactionService |
| AccountRestController | Account, AccountInput, AccountService, CreateAccountInput, InputValidator, constants |  |
| AccountService | Account, AccountRepository, CodeGenerator, TransactionRepository | AccountRestController, TransactionRestController |
| CodeGenerator | ACCOUNT_NUMBER_PATTERN_STRING, Generex, SORT_CODE_PATTERN_STRING | AccountService |
| CreateAccountInput |  | AccountRestController |
| Generex |  | CodeGenerator |
| InputValidator | constants | AccountRestController |
| SORT_CODE_PATTERN_STRING |  | CodeGenerator |
| Transaction |  | TransactionRepository, TransactionService |
| TransactionInput |  | TransactionService |
| TransactionRepository | Transaction | AccountService, TransactionService |
| TransactionRestController | ACTION, Account, AccountService, TransactionService, constants, utils |  |
| TransactionService | ACTION, Account, AccountRepository, Transaction, TransactionInput, TransactionRepository | TransactionRestController |
| constants |  | AccountRestController, InputValidator, TransactionRestController |
| utils |  | TransactionRestController |
