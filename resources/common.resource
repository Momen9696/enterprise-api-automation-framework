"""Shared suite setup and libraries."""

*** Settings ***
Library    framework.robot_libs.ApiKeywords.ApiKeywords
Library    framework.robot_libs.AuthKeywords.AuthKeywords
Library    framework.robot_libs.ValidationKeywords.ValidationKeywords
Library    framework.robot_libs.DataKeywords.DataKeywords
Library    framework.robot_libs.LedgerKeywords.LedgerKeywords

*** Keywords ***
Framework Is Ready
    ${env}=    Initialize Api Context
    Should Not Be Empty    ${env}
    ${health}=    Get Request    /health    use_auth=${False}
    Response Status Should Be    ${health}    200
    Response Should Match Schema    ${health}    health.schema.json
    Login As    admin
    Login As    customer
