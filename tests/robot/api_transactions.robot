"""Deposits, transfers, duplicate posts, and idempotency keys. All amounts are synthetic."""

*** Settings ***
Documentation    Ledger behavior for isolated customers.
Resource         ../../resources/transactions.resource
Suite Setup      Framework Is Ready

*** Test Cases ***
Transfer Is Idempotent And A Different Body Conflicts
    ${source_user}    ${source}=    Open Isolated Checking Account
    ${destination_user}    ${destination}=    Open Isolated Checking Account
    Login Created Customer    ${source_user}[email]
    ${funded}=    Post Transaction    ${source}[id]    deposit    80.00
    Response Status Should Be    ${funded}    201
    Response Should Match Schema    ${funded}    transaction.schema.json
    Response Field Should Be    ${funded}    idempotent_replay    ${False}
    ${key}=    New Idempotency Key
    ${first}=    Post Transaction    ${source}[id]    transfer    30.00    ${destination}[id]    ${key}
    Response Status Should Be    ${first}    201
    Response Field Should Be    ${first}    idempotent_replay    ${False}
    ${replay}=    Post Transaction    ${source}[id]    transfer    30.00    ${destination}[id]    ${key}
    Response Status Should Be    ${replay}    200
    Response Field Should Be    ${replay}    idempotent_replay    ${True}
    Should Be Equal    ${first}[body][id]    ${replay}[body][id]
    ${source_after}=    Get Request    /accounts/${source}[id]    role=dynamic
    Response Field Should Be    ${source_after}    balance    50.00
    ${conflict}=    Post Transaction    ${source}[id]    withdraw    1.00    ${EMPTY}    ${key}
    Response Status Should Be    ${conflict}    409
    Response Field Should Be    ${conflict}    code    idempotency_conflict
    ${first_debit}=    Post Transaction    ${source}[id]    withdraw    10.00
    ${second_debit}=    Post Transaction    ${source}[id]    withdraw    10.00
    Response Status Should Be    ${first_debit}    201
    Response Status Should Be    ${second_debit}    201
    Should Not Be Equal    ${first_debit}[body][id]    ${second_debit}[body][id]
    ${after_debits}=    Get Request    /accounts/${source}[id]    role=dynamic
    Response Field Should Be    ${after_debits}    balance    30.00
    Login Created Customer    ${destination_user}[email]
    ${destination_after}=    Get Request    /accounts/${destination}[id]    role=dynamic
    Response Field Should Be    ${destination_after}    balance    30.00

Insufficient Funds And Invalid Transfer
    ${user}    ${account}=    Open Isolated Checking Account
    ${same}=    Post Transaction    ${account}[id]    transfer    5.00    ${account}[id]
    Response Status Should Be    ${same}    422
    Response Field Should Be    ${same}    code    validation_error
    ${missing}=    Post Transaction    ${account}[id]    transfer    5.00
    Response Status Should Be    ${missing}    422
    Response Field Should Be    ${missing}    code    validation_error
    ${broke}=    Post Transaction    ${account}[id]    withdraw    5.00
    Response Status Should Be    ${broke}    422
    Response Field Should Be    ${broke}    code    insufficient_funds
    Should Not Be Empty    ${user}[id]

Generated Amount Deposit
    ${user}    ${account}=    Open Isolated Checking Account
    ${amount}=    Random Amount    1.00    20.00
    ${key}=    New Idempotency Key
    ${deposit}=    Post Transaction    ${account}[id]    deposit    ${amount}    ${EMPTY}    ${key}
    Response Status Should Be    ${deposit}    201
    Response Field Should Be    ${deposit}    amount    ${amount}
    Should Not Be Empty    ${user}[email]
