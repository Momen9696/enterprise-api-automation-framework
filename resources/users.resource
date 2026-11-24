"""User lifecycle keywords."""

*** Settings ***
Resource    common.resource

*** Keywords ***
Customer Profile Round Trip
    [Arguments]    ${full_name}=Round Trip
    ${user}=    Provision Customer    ${full_name}
    ${fetched}=    Get Request    /users/${user}[id]    role=admin
    Response Status Should Be    ${fetched}    200
    Response Should Match Schema    ${fetched}    user.schema.json
    RETURN    ${user}
