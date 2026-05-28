"use client";

import { fetchData } from "@/lib/api/fetchData";
import { useQuery } from "@tanstack/react-query";
import { Locale } from "../../../../i18n.config";
import IsLoadig from "../ISloading";
import { 
  FaCarAlt, 
  FaCheckCircle, 
  FaTimesCircle, 
  FaUserTie, 
  FaMoneyBillWave,
  FaChartLine,
  FaClock,
  FaUsers
} from "react-icons/fa";
import { formatDate } from "@/lib/FormatDate";

type TripStatus = "pending" | "accepted" | "driver_on_the_way" | "active" | "completed" | "cancelled";

type DashboardData = {
  trips: {
    total: number;
    by_status: Record<TripStatus, number>;
    by_period: {
      today: number;
      this_week: number;
      this_month: number;
      last_month: number;
    };
  };
  revenue: {
    total: number;
    total_trips: number;
    average_trip_value: number;
    by_period: {
      today: number;
      this_week: number;
      this_month: number;
      last_month: number;
    };
    unpaid: {
      amount: number;
      trips_count: number;
    };
  };
  drivers: {
    total: number;
    active: number;
    inactive: number;
    verified: number;
    unverified: number;
    with_completed_profile: number;
  };
  passengers: {
    total: number;
    active: number;
    inactive: number;
  };
  onboarding: {
    total: number;
    pending: number;
    step1_approved: number;
    step1_rejected: number;
    documents_uploaded: number;
    final_approved: number;
    final_rejected: number;
    needs_modification: number;
  };
  performance: {
    average_trip_value: number;
    cancellation_rate: number;
    completion_rate: number;
  };
  recent_activity: {
    trips: Array<{
      id: number;
      type: string;
      status: string;
      passenger_name: string;
      driver_name: string;
      cost: string;
      created_at: string;
    }>;
    onboarding: Array<{
      id: number;
      type: string;
      status: string;
      full_name: string;
      email: string;
      created_at: string;
    }>;
  };
};

function getStatusColor(status: string) {
  switch (status) {
    case "pending":
      return "bg-yellow-500/20 text-yellow-600 border-yellow-500";
    case "accepted":
    case "active":
      return "bg-blue-500/20 text-blue-600 border-blue-500";
    case "driver_on_the_way":
      return "bg-indigo-500/20 text-indigo-600 border-indigo-500";
    case "completed":
    case "final_approved":
      return "bg-green-500/20 text-green-600 border-green-500";
    case "cancelled":
    case "final_rejected":
    case "step1_rejected":
      return "bg-red-500/20 text-red-600 border-red-500";
    case "step1_approved":
      return "bg-emerald-500/20 text-emerald-600 border-emerald-500";
    case "documents_uploaded":
      return "bg-purple-500/20 text-purple-600 border-purple-500";
    case "needs_modification":
      return "bg-orange-500/20 text-orange-600 border-orange-500";
    default:
      return "bg-gray-500/20 text-gray-600 border-gray-500";
  }
}

export default function DashboardOverview({
  token,
  locale,
  trans,
}: {
  token?: string;
  locale: Locale;
  trans: any;
}) {
  const { data: dashboardData, isLoading } = useQuery<DashboardData>({
    queryKey: ["dashboard-overview"],
    queryFn: () => {
      return fetchData({
        endpoint: "/api/admin-panel/dashboard/overview/",
        token: token,
        queryParams: { locale: locale },
      });
    },
  });

  if (isLoading) {
    return <IsLoadig />;
  }

  if (!dashboardData) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">{trans.noData || "No data available"}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Main Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Trips Card */}
        <div className="bg-card rounded-xl border-2 border-blue-500/60 p-5 hover:border-blue-500/80 hover:shadow-lg hover:shadow-blue-500/20 transition-all duration-300">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-blue-500/30">
              <FaCarAlt className="text-white text-2xl" />
            </div>
            <div className="flex-1">
              <p className="text-xs font-medium text-muted-foreground mb-1">{trans.totalTrips || "Total Trips"}</p>
              <p className="text-3xl font-bold text-blue-600">{dashboardData.trips.total}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {trans.thisMonth || "This Month"}: {dashboardData.trips.by_period.this_month}
              </p>
            </div>
          </div>
        </div>

        {/* Revenue Card */}
        <div className="bg-card rounded-xl border-2 border-green-500/60 p-5 hover:border-green-500/80 hover:shadow-lg hover:shadow-green-500/20 transition-all duration-300" dir={locale === "ar" ? "rtl" : "ltr"}>
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-gradient-to-br from-green-500 to-green-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-green-500/30">
              <FaMoneyBillWave className="text-white text-2xl" />
            </div>
            <div className="flex-1">
              <p className="text-xs font-medium text-muted-foreground mb-1">{trans.totalRevenue || "Total Revenue"}</p>
              <p className="text-3xl font-bold text-green-600">£{dashboardData.revenue.total.toFixed(2)}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {trans.avgTrip || "Avg"}: £{dashboardData.revenue.average_trip_value.toFixed(2)}
              </p>
            </div>
          </div>
        </div>

        {/* Drivers Card */}
        <div className="bg-card rounded-xl border-2 border-purple-500/60 p-5 hover:border-purple-500/80 hover:shadow-lg hover:shadow-purple-500/20 transition-all duration-300">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-purple-500/30">
              <FaUserTie className="text-white text-2xl" />
            </div>
            <div className="flex-1">
              <p className="text-xs font-medium text-muted-foreground mb-1">{trans.totalDrivers || "Total Drivers"}</p>
              <p className="text-3xl font-bold text-purple-600">{dashboardData.drivers.total}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {trans.active || "Active"}: {dashboardData.drivers.active} 
              </p>
            </div>
          </div>
        </div>

        {/* Passengers Card */}
        <div className="bg-card rounded-xl border-2 border-orange-500/60 p-5 hover:border-orange-500/80 hover:shadow-lg hover:shadow-orange-500/20 transition-all duration-300">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-orange-500/30">
              <FaUsers className="text-white text-2xl" />
            </div>
            <div className="flex-1">
              <p className="text-xs font-medium text-muted-foreground mb-1">{trans.totalPassengers || "Total Passengers"}</p>
              <p className="text-3xl font-bold text-orange-600">{dashboardData.passengers.total}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {trans.active || "Active"}: {dashboardData.passengers.active}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Secondary Statistics - Trips by Status */}
      <div className="bg-card rounded-xl border-2 border-border p-6">
        <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
          <span className="w-1 h-6 bg-blue-500 rounded-full"></span>
          {trans.tripsByStatus || "Trips by Status"}
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {Object.entries(dashboardData.trips.by_status).map(([status, count]) => {
            const statusLabel = trans.status?.find((s: any) => s.value === status)?.title || status.replace(/_/g, " ");
            return (
              <div key={status} className="bg-muted p-4 rounded-lg border border-border">
                <p className="text-xs font-medium text-muted-foreground mb-1">{statusLabel}</p>
                <p className="text-2xl font-bold text-foreground">{count}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Performance Metrics & Onboarding Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Performance Metrics */}
        <div className="bg-card rounded-xl border-2 border-border p-6">
          <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
            <span className="w-1 h-6 bg-green-500 rounded-full"></span>
            {trans.performanceMetrics || "Performance Metrics"}
          </h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-muted rounded-lg border border-border">
              <span className="text-sm font-medium text-muted-foreground">{trans.avgTripValue || "Average Trip Value"}</span>
              <span className="text-xl font-bold text-green-600">£{dashboardData.performance.average_trip_value.toFixed(2)}</span>
            </div>
            <div className="flex items-center justify-between p-4 bg-muted rounded-lg border border-border">
              <span className="text-sm font-medium text-muted-foreground">{trans.completionRate || "Completion Rate"}</span>
              <span className="text-xl font-bold text-blue-600">{dashboardData.performance.completion_rate.toFixed(1)}%</span>
            </div>
            <div className="flex items-center justify-between p-4 bg-muted rounded-lg border border-border">
              <span className="text-sm font-medium text-muted-foreground">{trans.cancellationRate || "Cancellation Rate"}</span>
              <span className="text-xl font-bold text-red-600">{dashboardData.performance.cancellation_rate.toFixed(1)}%</span>
            </div>
          </div>
        </div>

        {/* Onboarding Status */}
        <div className="bg-card rounded-xl border-2 border-border p-6">
          <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
            <span className="w-1 h-6 bg-yellow-500 rounded-full"></span>
            {trans.onboardingStatus || "Driver Onboarding Status"}
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-muted p-3 rounded-lg border border-border">
              <p className="text-xs font-medium text-muted-foreground mb-1">{trans.total || "Total"}</p>
              <p className="text-xl font-bold text-foreground">{dashboardData.onboarding.total}</p>
            </div>
            <div className="bg-muted p-3 rounded-lg border border-yellow-500/50">
              <p className="text-xs font-medium text-muted-foreground mb-1">{trans.pending || "Pending"}</p>
              <p className="text-xl font-bold text-yellow-600">{dashboardData.onboarding.pending}</p>
            </div>
            <div className="bg-muted p-3 rounded-lg border border-green-500/50">
              <p className="text-xs font-medium text-muted-foreground mb-1">{trans.approved || "Approved"}</p>
              <p className="text-xl font-bold text-green-600">{dashboardData.onboarding.step1_approved}</p>
            </div>
            <div className="bg-muted p-3 rounded-lg border border-emerald-500/50">
              <p className="text-xs font-medium text-muted-foreground mb-1">{trans.finalApproved || "Final Approved"}</p>
              <p className="text-xl font-bold text-emerald-600">{dashboardData.onboarding.final_approved}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Revenue Details */}
      <div className="bg-card rounded-xl border-2 border-border p-6">
        <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
          <span className="w-1 h-6 bg-green-500 rounded-full"></span>
          {trans.revenueBreakdown || "Revenue Breakdown"}
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-muted p-4 rounded-lg border border-border">
            <p className="text-xs font-medium text-muted-foreground mb-1">{trans.today || "Today"}</p>
            <p className="text-2xl font-bold text-green-600">£{dashboardData.revenue.by_period.today.toFixed(2)}</p>
          </div>
          <div className="bg-muted p-4 rounded-lg border border-border">
            <p className="text-xs font-medium text-muted-foreground mb-1">{trans.thisWeek || "This Week"}</p>
            <p className="text-2xl font-bold text-green-600">£{dashboardData.revenue.by_period.this_week.toFixed(2)}</p>
          </div>
          <div className="bg-muted p-4 rounded-lg border border-border">
            <p className="text-xs font-medium text-muted-foreground mb-1">{trans.thisMonth || "This Month"}</p>
            <p className="text-2xl font-bold text-green-600">£{dashboardData.revenue.by_period.this_month.toFixed(2)}</p>
          </div>
          <div className="bg-muted p-4 rounded-lg border border-border">
            <p className="text-xs font-medium text-muted-foreground mb-1">{trans.lastMonth || "Last Month"}</p>
            <p className="text-2xl font-bold text-green-600">£{dashboardData.revenue.by_period.last_month.toFixed(2)}</p>
          </div>
        </div>
        {dashboardData.revenue.unpaid.amount > 0 && (
          <div className="mt-4 p-4 bg-red-500/10 border-2 border-red-500/50 rounded-lg">
            <p className="text-sm font-semibold text-red-600">
              {trans.unpaidRevenue || "Unpaid Revenue"}: £{dashboardData.revenue.unpaid.amount.toFixed(2)} ({dashboardData.revenue.unpaid.trips_count} {trans.tripsLabel || "trips"})
            </p>
          </div>
        )}
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Recent Trips */}
        <div className="bg-card rounded-xl border-2 border-border p-6">
          <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
            <span className="w-1 h-6 bg-blue-500 rounded-full"></span>
            {trans.recentTrips || "Recent Trips"}
          </h3>
          <div className="space-y-3 max-h-96 overflow-y-auto on-scrollbar">
            {dashboardData.recent_activity.trips.length > 0 ? (
              dashboardData.recent_activity.trips.map((trip) => (
                <div key={trip.id} className="bg-muted p-4 rounded-lg border border-border hover:border-primary/50 transition-colors">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <p className="font-semibold text-foreground">#{trip.id} - {trip.passenger_name}</p>
                      <p className="text-sm text-muted-foreground">
                        {trans.driverLabel || "Driver"}: {trip.driver_name}
                      </p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-bold border ${getStatusColor(trip.status)}`}>
                      {trans.status?.find((s: any) => s.value === trip.status)?.title || trip.status.replace(/_/g, " ")}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-green-600 font-bold">£{parseFloat(trip.cost).toFixed(2)}</span>
                    <span className="text-muted-foreground text-xs">{formatDate(new Date(trip.created_at), locale)}</span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-center text-muted-foreground py-8">{trans.noRecentTrips || "No recent trips"}</p>
            )}
          </div>
        </div>

        {/* Recent Onboarding */}
        <div className="bg-card rounded-xl border-2 border-border p-6">
          <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
            <span className="w-1 h-6 bg-yellow-500 rounded-full"></span>
            {trans.recentOnboarding || "Recent Onboarding"}
          </h3>
          <div className="space-y-3 max-h-96 overflow-y-auto on-scrollbar">
            {dashboardData.recent_activity.onboarding.length > 0 ? (
              dashboardData.recent_activity.onboarding.map((item) => (
                <div key={item.id} className="bg-muted p-4 rounded-lg border border-border hover:border-primary/50 transition-colors">
                  <div className="flex flex-col gap-2 mb-2">
                    <div className="flex-1">
                      <p className="font-semibold text-foreground">{item.full_name}</p>
                      <p className="text-sm text-muted-foreground">{item.email}</p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-bold border ${getStatusColor(item.status)}`}>
                      {trans.statusTitles?.[item.status as keyof typeof trans.statusTitles] || item.status.replace(/_/g, " ")}
                    </span>
                  </div>
                  <p className="text-muted-foreground text-xs">{formatDate(new Date(item.created_at), locale)}</p>
                </div>
              ))
            ) : (
              <p className="text-center text-muted-foreground py-8">{trans.noRecentOnboarding || "No recent onboarding"}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

