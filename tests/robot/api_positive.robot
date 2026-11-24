"""Successful calls for every HTTP method, pagination, and an empty page."""

*** Settings ***
Documentation    Happy-path coverage against the local ledger API.
Resource         ../../resources/auth.resource
Resource         ../../resources/users.resource
Resource         ../../resources/accounts.resource
Suite Setup      Framework Is Ready

*** Test Cases ***
Seeded Customer Session Works
    Seeded Customer Can Read Own Accounts

Create Read Update And Delete User
    ${user}=    Customer Profile Round Trip    Patch Target
    ${put_body}=    Create Dictionary    full_name=Replaced Name
    ${replaced}=    Put Request    /users/${user}[id]    ${put_body}    role=admin
    Response Status Should Be    ${replaced}    200
    Response Field Should Be    ${replaced}    full_name    Replaced Name
    Response Should Match Schema    ${replaced}    user.schema.json
    ${patch_body}=    Create Dictionary    full_name=Patched Name
    ${patched}=    Patch Request    /users/${user}[id]    ${patch_body}    role=admin
    Response Status Should Be    ${patched}    200
    Response Field Should Be    ${patched}    full_name    Patched Name
    ${deleted}=    Delete Request    /users/${user}[id]    role=admin
    Response Status Should Be    ${deleted}    204
    Should Be Equal    ${deleted}[body]    ${NONE}
    ${missing}=    Get Request    /users/${user}[id]    role=admin
    Response Status Should Be    ${missing}    404
    Response Should Match Schema    ${missing}    error.schema.json

Customer Sees Only Their Accounts And An Empty Page
    ${user}    ${account}=    Open Isolated Checking Account
    ${savings}=    Create Dictionary    account_type=savings    currency=USD
    ${second}=    Post Request    /accounts    ${savings}    role=dynamic
    Response Status Should Be    ${second}    201
    ${third_body}=    Create Dictionary    account_type=checking    currency=USD
    ${third}=    Post Request    /accounts    ${third_body}    role=dynamic
    Response Status Should Be    ${third}    201
    ${page}=    Create Dictionary    page=${1}    page_size=${2}
    ${first}=    Get Request    /accounts    role=dynamic    params=${page}
    Response Status Should Be    ${first}    200
    Page Items Should Match Schema    ${first}    account.schema.json
    Length Should Be    ${first}[body][items]    2
    Should Be Equal As Integers    ${first}[body][total]    3
    ${next}=    Create Dictionary    page=${2}    page_size=${2}
    ${second_page}=    Get Request    /accounts    role=dynamic    params=${next}
    Length Should Be    ${second_page}[body][items]    1
    ${empty}=    Create Dictionary    page=${9}    page_size=${2}
    ${empty_page}=    Get Request    /accounts    role=dynamic    params=${empty}
    Response Status Should Be    ${empty_page}    200
    Length Should Be    ${empty_page}[body][items]    0
    Should Be Equal As Integers    ${empty_page}[body][total]    3
    Should Not Be Empty    ${account}[id]
    Should Be Equal    ${user}[role]    customer
