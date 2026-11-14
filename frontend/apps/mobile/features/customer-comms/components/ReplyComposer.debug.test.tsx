import React from "react";
import { render, screen } from "@testing-library/react-native";
import { Pressable, Text } from "react-native";

it("debug pressable", () => {
  render(
    <Pressable disabled={true} testID="btn">
      <Text>Btn</Text>
    </Pressable>,
  );
  const btn = screen.getByTestId("btn");
  console.log(Object.keys(btn.props));
  console.log(btn.props.accessibilityState);
  console.log(btn.props.disabled);
});
