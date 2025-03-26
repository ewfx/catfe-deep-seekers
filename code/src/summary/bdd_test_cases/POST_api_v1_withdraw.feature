# BDD Test Cases for POST api/v1/withdraw

Feature: Withdrawal from Account
As a user, I want to withdraw money from my account so that I can use it for my personal needs.

Scenario 1: Successful Withdrawal
Given I am an authenticated user with a valid account
And I have sufficient balance in my account
When I send a POST request to "api/v1/withdraw" with a valid withdrawal amount
Then I should receive a 200 OK response
And the withdrawal amount should be deducted from my account balance

Scenario 2: Insufficient Balance
Given I am an authenticated user with a valid account
And I have insufficient balance in my account
When I send a POST request to "api/v1/withdraw" with a withdrawal amount greater than my account balance
Then I should receive a 400 Bad Request response
And the response message should indicate that I have insufficient balance

Scenario 3: Unauthenticated Withdrawal Attempt
Given I am not an authenticated user
When I send a POST request to "api/v1/withdraw" with a withdrawal amount
Then I should receive a 401 Unauthorized response
And the response message should indicate that I need to authenticate

Scenario 4: Withdrawal with Invalid Amount
Given I am an authenticated user with a valid account
When I send a POST request to "api/v1/withdraw" with an invalid withdrawal amount (e.g., negative amount, non-numeric value)
Then I should receive a 400 Bad Request response
And the response message should indicate that the withdrawal amount is invalid

Scenario 5: Withdrawal from Non-existent Account
Given I am an authenticated user
And I try to withdraw from a non-existent account
When I send a POST request to "api/v1/withdraw"
Then I should receive a 404 Not Found response
And the response message should indicate that the account does not exist