import {
  SquaresFour, CalendarBlank, PlusCircle, ClockCounterClockwise,
  ChartBar, Gear, SignOut, Download, CaretLeft, CaretRight, X,
  HeartStraight, Globe, List,
} from '@phosphor-icons/react'

// Central icon registry — Phosphor (default weight), sizes via props.
export const icons = {
  home: <SquaresFour size={20} />,
  calendar: <CalendarBlank size={20} />,
  plus: <PlusCircle size={20} />,
  history: <ClockCounterClockwise size={20} />,
  insights: <ChartBar size={20} />,
  settings: <Gear size={20} />,
  logout: <SignOut size={18} />,
  download: <Download size={18} />,
  left: <CaretLeft size={18} weight="bold" />,
  right: <CaretRight size={18} weight="bold" />,
  close: <X size={18} weight="bold" />,
  heart: <HeartStraight size={18} />,
  globe: <Globe size={18} />,
  menu: <List size={22} />,
}
