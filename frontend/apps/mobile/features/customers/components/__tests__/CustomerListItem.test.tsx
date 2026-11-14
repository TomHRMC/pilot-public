/**
 * CustomerListItem unit tests (MOB-B3)
 *
 * Location: apps/mobile/features/customers/components/__tests__/CustomerListItem.test.tsx
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { CustomerListItem } from "../CustomerListItem";
import type { CustomerListItem as CustomerListItemData } from "../../hooks/useCustomers";

function makeCustomer(
  overrides: Partial<CustomerListItemData> = {},
): CustomerListItemData {
  return {
    id: "customer-001",
    tenant_id: "tenant-001",
    type: "residential",
    display_name: "John Smith",
    first_name: "John",
    last_name: "Smith",
    company_name: null,
    email: "john@example.com",
    ...overrides,
  };
}

describe("CustomerListItem", () => {
  it("renders display_name", () => {
    render(
      <CustomerListItem
        customer={makeCustomer({ display_name: "John Smith" })}
        onPress={() => {}}
      />,
    );
    expect(screen.getByText("John Smith")).toBeTruthy();
  });

  it("renders 'Residential' badge for type=residential", () => {
    render(
      <CustomerListItem
        customer={makeCustomer({ type: "residential" })}
        onPress={() => {}}
      />,
    );
    expect(screen.getByText("Residential")).toBeTruthy();
  });

  it("renders 'Commercial' badge for type=commercial", () => {
    render(
      <CustomerListItem
        customer={makeCustomer({
          type: "commercial",
          company_name: "Acme Corp",
        })}
        onPress={() => {}}
      />,
    );
    expect(screen.getByText("Commercial")).toBeTruthy();
  });

  it("renders unknown type string as badge label for unexpected type", () => {
    render(
      <CustomerListItem
        customer={makeCustomer({ type: "government" })}
        onPress={() => {}}
      />,
    );
    expect(screen.getByText("government")).toBeTruthy();
  });

  it("renders email when present", () => {
    render(
      <CustomerListItem
        customer={makeCustomer({ email: "john@example.com" })}
        onPress={() => {}}
      />,
    );
    expect(screen.getByText("john@example.com")).toBeTruthy();
  });

  it("does not render email text when email is null", () => {
    render(
      <CustomerListItem
        customer={makeCustomer({ email: null })}
        onPress={() => {}}
      />,
    );
    expect(screen.queryByText(/@/)).toBeNull();
  });

  it("does not crash when email is null", () => {
    expect(() =>
      render(
        <CustomerListItem
          customer={makeCustomer({ email: null })}
          onPress={() => {}}
        />,
      ),
    ).not.toThrow();
  });

  it("calls onPress with customer.id when tapped", () => {
    const onPress = jest.fn();
    render(
      <CustomerListItem
        customer={makeCustomer({ id: "customer-abc" })}
        onPress={onPress}
        testID="customer-row-test"
      />,
    );
    fireEvent.press(screen.getByTestId("customer-row-test"));
    expect(onPress).toHaveBeenCalledWith("customer-abc");
  });

  it("uses testID prop when provided", () => {
    render(
      <CustomerListItem
        customer={makeCustomer()}
        onPress={() => {}}
        testID="custom-test-id"
      />,
    );
    expect(screen.getByTestId("custom-test-id")).toBeTruthy();
  });

  it("uses default testID based on customer.id when testID not provided", () => {
    render(
      <CustomerListItem
        customer={makeCustomer({ id: "customer-001" })}
        onPress={() => {}}
      />,
    );
    expect(screen.getByTestId("customer-row-customer-001")).toBeTruthy();
  });
});
