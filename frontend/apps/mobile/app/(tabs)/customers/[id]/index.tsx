import { useLocalSearchParams } from "expo-router";
import { CustomerDetailScreen } from "@/features/customers/components/CustomerDetailScreen";

export default function CustomerDetailRoute() {
  const { id: customerId } = useLocalSearchParams<{ id: string }>();
  return <CustomerDetailScreen customerId={customerId} />;
}
