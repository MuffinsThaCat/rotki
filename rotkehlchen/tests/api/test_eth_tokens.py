from http import HTTPStatus

import pytest
import requests
from typing_extensions import Literal

from rotkehlchen.constants.assets import A_DAI
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.blockchain import assert_eth_balances_result
from rotkehlchen.tests.utils.constants import A_GNO, A_MKR, A_RDN
from rotkehlchen.tests.utils.rotkehlchen import setup_balances


@pytest.mark.parametrize('owned_eth_tokens', [[A_RDN, A_GNO]])
def test_query_ethereum_tokens_info(rotkehlchen_api_server):
    """Test that the rest api endpoint to query information about ethereum tokens works fine"""
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "ethereumtokensresource",
    ))

    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    # There should be 2 keys in the result dict
    assert len(data['result']) == 2
    all_tokens = data['result']['all_eth_tokens']
    assert isinstance(all_tokens, list)
    for entry in all_tokens:
        assert len(entry) == 4
        assert entry['address'] is not None
        assert entry['symbol'] is not None
        assert entry['name'] is not None
        assert entry['decimal'] >= 0 and entry['decimal'] <= 18

    assert data['result']['owned_eth_tokens'] == ['RDN', 'GNO']


def assert_modifying_ethereum_tokens(server, data, ethereum_accounts, setup, expected_tokens):
    """Helper function to test the outcome of adding/removing ethereum tokens via the API"""
    assert_eth_balances_result(
        rotki=server.rest_api.rotkehlchen,
        json_data=data,
        eth_accounts=ethereum_accounts,
        eth_balances=setup.eth_balances,
        token_balances=setup.token_balances,
        also_btc=False,
    )
    # And also query tokens to see that it's properly added to the tracked tokens
    response = requests.get(api_url_for(
        server,
        "ethereumtokensresource",
    ))
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert data['result']['owned_eth_tokens'] == expected_tokens


@pytest.mark.parametrize('owned_eth_tokens', [[A_DAI, A_GNO]])
@pytest.mark.parametrize('number_of_eth_accounts', [2])
def test_adding_ethereum_tokens(
        rotkehlchen_api_server,
        ethereum_accounts,
):
    """Test that the rest api endpoint to add new ethereum tokens works properly"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        token_balances={
            A_RDN: ['0', '4000000'],
            A_DAI: ['50000000', '0'],
            A_MKR: ['1115000', '0'],
            A_GNO: ['0', '455552222'],
        },
        btc_accounts=[],
    )

    # Add RDN and MKR as tracked tokens and make sure that the rdn balance checks out
    with setup.etherscan_patch, setup.alethio_patch:
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            "ethereumtokensresource",
        ), json={'eth_tokens': ['RDN', 'MKR']})

    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert_modifying_ethereum_tokens(
        rotkehlchen_api_server,
        json_data,
        ethereum_accounts,
        setup,
        ['DAI', 'GNO', 'RDN', 'MKR'],
    )


@pytest.mark.parametrize('owned_eth_tokens', [[A_DAI, A_GNO]])
@pytest.mark.parametrize('number_of_eth_accounts', [2])
def test_adding_ethereum_tokens_async(
        rotkehlchen_api_server,
        ethereum_accounts,
):
    """Test calling the rest api endpoint to add new ethereum tokens works asynchronously"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        token_balances={
            A_RDN: ['0', '4000000'],
            A_DAI: ['50000000', '0'],
            A_MKR: ['1115000', '0'],
            A_GNO: ['0', '455552222'],
        },
        btc_accounts=[],
    )

    # Add RDN and MKR as tracked tokens and make sure that the rdn balance checks out
    with setup.etherscan_patch, setup.alethio_patch:
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            "ethereumtokensresource",
        ), json={'eth_tokens': ['RDN', 'MKR'], 'async_query': True})
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
    assert_modifying_ethereum_tokens(
        rotkehlchen_api_server,
        outcome,
        ethereum_accounts,
        setup,
        ['DAI', 'GNO', 'RDN', 'MKR'],
    )


def check_modifying_eth_tokens_error_responses(
        rotkehlchen_api_server,
        method: Literal['put', 'delete'],
) -> None:
    """Convenience function to check error response of adding/removing ethereum token endpoints"""
    # See that omitting eth_tokens is an error
    response = getattr(requests, method)(api_url_for(
        rotkehlchen_api_server,
        "ethereumtokensresource",
    ), json={})
    assert_error_response(
        response=response,
        contained_in_msg='eth_tokens": ["Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # See that providing invalid type for eth_tokens is an error
    response = getattr(requests, method)(api_url_for(
        rotkehlchen_api_server,
        "ethereumtokensresource",
    ), json={'eth_tokens': {}})
    assert_error_response(
        response=response,
        contained_in_msg='"eth_tokens": ["Not a valid list."',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # See that providing invalid type for eth_tokens is an error
    response = getattr(requests, method)(api_url_for(
        rotkehlchen_api_server,
        "ethereumtokensresource",
    ), json={'eth_tokens': {}})
    assert_error_response(
        response=response,
        contained_in_msg='"eth_tokens": ["Not a valid list."',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # See that providing invalid type for a single eth token is an error
    response = getattr(requests, method)(api_url_for(
        rotkehlchen_api_server,
        "ethereumtokensresource",
    ), json={'eth_tokens': [55, 'RDN']})
    assert_error_response(
        response=response,
        contained_in_msg='Tried to initialize an asset out of a non-string identifier',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # See that providing invalid asset for a single eth token is an error
    response = getattr(requests, method)(api_url_for(
        rotkehlchen_api_server,
        "ethereumtokensresource",
    ), json={'eth_tokens': ['NOTATOKEN', 'RDN']})
    assert_error_response(
        response=response,
        contained_in_msg='Unknown asset NOTATOKEN provided.',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # See that providing a non-ethereum-token asset is an error
    response = getattr(requests, method)(api_url_for(
        rotkehlchen_api_server,
        "ethereumtokensresource",
    ), json={'eth_tokens': ['BTC', 'RDN']})
    assert_error_response(
        response=response,
        contained_in_msg='Tried to initialize a non Ethereum asset as Ethereum Token',
        status_code=HTTPStatus.BAD_REQUEST,
    )


def test_adding_ethereum_tokens_errors(rotkehlchen_api_server):
    """Test that the rest api endpoint to add new ethereum tokens handles errors properly"""
    check_modifying_eth_tokens_error_responses(rotkehlchen_api_server, method='put')


@pytest.mark.parametrize('owned_eth_tokens', [[A_DAI, A_GNO, A_RDN]])
@pytest.mark.parametrize('number_of_eth_accounts', [2])
def test_removing_ethereum_tokens(
        rotkehlchen_api_server,
        ethereum_accounts,
):
    """Test that the rest api endpoint to add new ethereum tokens works properly"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        token_balances={
            A_RDN: ['0', '0'],
            A_DAI: ['50000000', '0'],
            A_GNO: ['0', '0'],
        },
        btc_accounts=[],
    )

    # Remove GNO and RDN as tracked tokens and make sure that the dai balance checks out
    with setup.etherscan_patch, setup.alethio_patch:
        response = requests.delete(api_url_for(
            rotkehlchen_api_server,
            "ethereumtokensresource",
        ), json={'eth_tokens': ['GNO', 'RDN']})

    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert_modifying_ethereum_tokens(
        rotkehlchen_api_server,
        json_data,
        ethereum_accounts,
        setup,
        ['DAI'],
    )


@pytest.mark.parametrize('owned_eth_tokens', [[A_DAI, A_GNO, A_RDN]])
@pytest.mark.parametrize('number_of_eth_accounts', [2])
def test_removing_ethereum_tokens_async(
        rotkehlchen_api_server,
        ethereum_accounts,
):
    """Test that the rest api endpoint to add new ethereum tokens works properly"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        token_balances={
            A_RDN: ['0', '0'],
            A_DAI: ['50000000', '0'],
            A_GNO: ['0', '0'],
        },
        btc_accounts=[],
    )

    # Remove GNO and RDN as tracked tokens and make sure that the dai balance checks out
    with setup.etherscan_patch, setup.alethio_patch:
        response = requests.delete(api_url_for(
            rotkehlchen_api_server,
            "ethereumtokensresource",
        ), json={'eth_tokens': ['GNO', 'RDN'], 'async_query': True})
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
    assert_modifying_ethereum_tokens(
        rotkehlchen_api_server,
        outcome,
        ethereum_accounts,
        setup,
        ['DAI'],
    )


def test_removing_ethereum_tokens_errors(rotkehlchen_api_server):
    """Test that the rest api endpoint to remove ethereum tokens handles errors properly"""
    check_modifying_eth_tokens_error_responses(rotkehlchen_api_server, method='delete')
