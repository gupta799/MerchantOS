from __future__ import annotations

from app.computer.protocol import ComputerClient, ComputerContinueRequest, ComputerStartRequest, ComputerTurn
from app.ids import ComputerCallId, ComputerResponseId, new_action_id
from app.models import ComputerAction, ComputerActionType


class ScriptedComputerClient(ComputerClient):
    async def start(self, request: ComputerStartRequest) -> ComputerTurn:
        return ComputerTurn(
            response_id=ComputerResponseId("scripted_response_1"),
            call_id=ComputerCallId("scripted_call_1"),
            actions=[
                ComputerAction(
                    type=ComputerActionType.CLICK,
                    action_id=new_action_id(),
                    x=360,
                    y=486,
                    reason="Select 10.5 Wide",
                )
            ],
            completed=False,
            message="Scripted variant selection",
        )

    async def continue_turn(self, request: ComputerContinueRequest) -> ComputerTurn:
        selected_variant = request.observation.dom_summary.selected_variant_id is not None
        cart_count = request.observation.dom_summary.cart_count
        if selected_variant and cart_count == 0:
            return ComputerTurn(
                response_id=ComputerResponseId("scripted_response_2"),
                call_id=ComputerCallId("scripted_call_2"),
                actions=[
                    ComputerAction(
                        type=ComputerActionType.CLICK,
                        action_id=new_action_id(),
                        x=640,
                        y=552,
                        reason="Add StormRunner GTX to cart",
                    )
                ],
                completed=False,
                message="Scripted add to cart",
            )
        return ComputerTurn(
            response_id=ComputerResponseId("scripted_response_done"),
            call_id=None,
            actions=[],
            completed=True,
            message="StormRunner GTX is in the cart",
        )

