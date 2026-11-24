"""Excel and JSON cases. Each row creates isolated synthetic records."""

*** Settings ***
Documentation    Data-driven user, account, and amount scenarios.
Resource         ../../resources/transactions.resource
Suite Setup      Framework Is Ready

*** Test Cases ***
Json User Cases
    ${rows}=    Load Json Cases    test_data/json/users.json
    FOR    ${row}    IN    @{rows}
        ${response}=    Run User Row    ${row}
        Assert Status From Row    ${response}    ${row}    user.schema.json
    END

Json Account Cases
    ${rows}=    Load Json Cases    test_data/json/accounts.json
    FOR    ${row}    IN    @{rows}
        ${response}=    Run Account Row    ${row}
        Assert Status From Row    ${response}    ${row}    account.schema.json
    END

Json Transaction Cases
    ${rows}=    Load Json Cases    test_data/json/transactions.json
    FOR    ${row}    IN    @{rows}
        ${response}=    Run Amount Row    ${row}
        Assert Status From Row    ${response}    ${row}    transaction.schema.json
    END

Excel User Account And Boundary Cases
    ${users}=    Load Excel Cases    test_data/excel/api_cases.xlsx    users
    FOR    ${row}    IN    @{users}
        ${response}=    Run User Row    ${row}
        Assert Status From Row    ${response}    ${row}    user.schema.json
    END
    ${accounts}=    Load Excel Cases    test_data/excel/api_cases.xlsx    accounts
    FOR    ${row}    IN    @{accounts}
        ${response}=    Run Account Row    ${row}
        Assert Status From Row    ${response}    ${row}    account.schema.json
    END
    ${amounts}=    Load Excel Cases    test_data/excel/api_cases.xlsx    boundaries
    FOR    ${row}    IN    @{amounts}
        ${response}=    Run Amount Row    ${row}
        Assert Status From Row    ${response}    ${row}    transaction.schema.json
    END
