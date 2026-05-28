import { Locale } from "../../i18n.config";
import { format } from "date-fns";

  function getOrdinal(n: number) {
    const s = ["th", "st", "nd", "rd"];
    const v = n % 100;
    return s[(v - 20) % 10] || s[v] || s[0];
  }

 export const formatDate = (date: Date ,locale:Locale) => {
    if (locale === "ar") {
      return format(date, "d/M/yyyy", {});
    } else {
      const day = date.getDate();
      const monthYear = format(date, "MMMM yyyy", {});
      return `${day}${getOrdinal(day)} ${monthYear}`;
    }
  };
