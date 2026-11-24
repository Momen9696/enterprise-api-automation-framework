"""Authentication checks that do not print tokens."""

*** Settings ***
Resource    common.resource

*** Keywords ***
Seeded Customer Can Read Own Accounts
    ${response}=    Get Request    /accounts    role=customer
    Response Status Should Be    ${response}    200
    Page Items Should Match Schema    ${response}    account.schema.json
