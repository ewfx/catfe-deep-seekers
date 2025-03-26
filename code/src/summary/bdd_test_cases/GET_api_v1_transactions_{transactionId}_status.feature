# BDD Test Cases for GET api/v1/transactions/{transactionId}/status

Feature: Transaction Status Retrieval
As a user, I want to be able to retrieve the status of a specific transaction so that I can keep track of my financial activities.

Scenario: Retrieve the status of a valid transaction
Given a user has made a transaction with transactionId
When the user requests the status of the transaction with the valid transactionId
Then the system should return the status of the transaction

Scenario: Retrieve the status of a non-existent transaction
Given a user requests the status of a transaction
When the user provides a transactionId that does not exist
Then the system should return an error message indicating that the transaction does not exist

Scenario: Retrieve the status of a transaction without providing a transactionId
Given a user requests the status of a transaction
When the user does not provide a transactionId
Then the system should return an error message indicating that the transactionId is required

Scenario: Retrieve the status of a transaction with an invalid transactionId format
Given a user requests the status of a transaction
When the user provides a transactionId in an invalid format
Then the system should return an error message indicating that the transactionId format is invalid

Scenario: Retrieve the status of a transaction without being authenticated
Given a user requests the status of a transaction
When the user is not authenticated
Then the system should return an error message indicating that authentication is required

Scenario: Retrieve the status of a transaction without having the necessary authorization
Given a user requests the status of a transaction
When the user does not have the necessary authorization
Then the system should return an error message indicating that the user does not have the necessary authorization to access the transaction status